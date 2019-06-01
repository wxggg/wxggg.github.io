Tensorflow 源码中python API和底层c/c++之间的关联主要是靠 `SWIG` 来完成的，这是一个用于把C/C++集成到其他语言中的编译器。本文主要介绍swig以及tensorflow如何利用swig关联前后端，另外主要介绍了一下Session的生命周期。

http://www.swig.org/


## SWIG实例之python调用C
首先准备C语言函数
```c++
/* File : example.c */
#include <time.h>
double My_variable = 3.0;

int fact(int n) {
    if (n <= 1) return 1;
    else return n*fact(n-1);
}
int my_mod(int x, int y) {
    return (x%y);
}
char *get_time()
{
    time_t ltime;
    time(&ltime);
    return ctime(&ltime);
}
```
然后准备swig interface接口文件
```c
/* example.i */
%module example
%{
/* Put header files here or function declarations like below */
extern double My_variable;
extern int fact(int n);
extern int my_mod(int x, int y);
extern char *get_time();
%}

extern double My_variable;
extern int fact(int n);
extern int my_mod(int x, int y);
extern char *get_time();
```
### 编译
需要安装swig，Ubuntu环境执行 `sudo apt-get install swig `，然后执行如下指令，会生产`example.py` 和 `example_wrap.c` 两个文件
```perl
$swig -python example.i
```
在`example_wrap.c` 中可以找到一个静态的函数符号表如下，这里将python调用名称如`get_time`与包装的函数`_wrap_get_time`进行连接起来，匹配对应的C函数实现，最终在`example.c`中找到具体实现
```c
static PyMethodDef SwigMethods[] = {
	 { (char *)"SWIG_PyInstanceMethod_New", (PyCFunction)SWIG_PyInstanceMethod_New, METH_O, NULL},
	 { (char *)"fact", _wrap_fact, METH_VARARGS, NULL},
	 { (char *)"my_mod", _wrap_my_mod, METH_VARARGS, NULL},
	 { (char *)"get_time", _wrap_get_time, METH_VARARGS, NULL},
	 { NULL, NULL, 0, NULL }
};
```

然后利用gcc编译C语言文件，注意这里`-I`需要输入python的include目录，若报错  _fatal error: Python.h: No such file or director_ 说明目录没有设置正确，可以使用`locate Python.h`查找include目录，tensorflow使用的是python 2.7所以这里执行如下
```perl
$gcc -c example.c example_wrap.c -I/usr/include/python2.7
```
执行完后生成对应的`.o`目标文件，然后链接成共享库
```perl
$ld -shared example.o example_wrap.o -o _example.so
```
到这里时执行会报错，_ld: example_wrap.o: relocation R_X86_64_32S against .rodata can not be used when making a shared object; recompile with -fPIC_

这里在上一个环节gcc编译的时候加上`-fPIC`即可，如 `gcc -fPIC -c ...`，然后再执行对应的链接`ld`操作，就可以生成对应的共享库 `_example.so`

### 使用python模块
可以如下用Python调用example中的函数
```python
>>> import example
>>> example.fact(5)
120
>>> example.my_mod(7,3)
1
>>> example.get_time()
'Sun Mar 18 12:59:22 2018\n'
>>>
```

## Tensorflow中Session生命周期
tensorflow利用swig包装C/C++实现系统，tensorflow使用Bazel来构建，在编译之前启动swig的代码生成过程，tensorflow中Session的swig接口文件为 `tf_session.i` 会生成适配文件：`pywrap_tensorflow.py` 和 `pywrap_tensorflow.cpp`，在编译之后会生成共享库 `_pywrap_tensorflow.so`。

类似于上述的swig例子，在`pywrap_tensorflow.cpp`中同样静态注册了一个函数符号表，在运行时会对Python的函数名称匹配找到对应的C函数实现，最终转到`c_api.c`

![](https://upload-images.jianshu.io/upload_images/2254249-6b09734b9eb93e83.png)

### Session 在Python中的创建过程
当client启动Session执行之前，先创建一个Session实例，进而调用父类BaseSession的构造函数，这里开始调用swig创建的包装Python库`pywrap_tensorflow`的函数
`tf_session.TF_NewSessionOptions`等来创建或删除Session 。 而且从BaseSession的构造函数中也可以看到，如果没有初始化graph的话，会调用一个default的graph
```python
# tensorflow/python/client/session.py
from tensorflow.python import pywrap_tensorflow as tf_session

class BaseSession(SessionInterface):
  def __init__(self, target='', graph=None, config=None):
    # other code
    if graph is None:
      self._graph = ops.get_default_graph()
    # other code
    self._session = None
    opts = tf_session.TF_NewSessionOptions(target=self._target, config=config)
    try:
      with errors.raise_exception_on_not_ok_status() as status:
        if self._created_with_new_api:
          self._session = tf_session.TF_NewSession(self._graph._c_graph, opts,
        else:
          self._session = tf_session.TF_NewDeprecatedSession(opts, status)
    finally:
      tf_session.TF_DeleteSessionOptions(opts)
    # other code
```
从这里开始就经过swig包装的中间层之后，就能够调用共享库中的C语言API了，同样在`pywrap_tensorflow.cpp`中也静态注册了函数调用的符号表

### Session 在C/C++中的生命周期
以调用新API为例，在BaseSession的初始化时会调用pywrap_tensorflow的TF_NewSession，并进一步通过swig调用c_api中的函数`TF_NewSession`
```c
TF_Session* TF_NewSession(TF_Graph* graph, const TF_SessionOptions* opt,
                          TF_Status* status) {
  Session* session;
  status->status = NewSession(opt->options, &session);
  if (status->status.ok()) {
    TF_Session* new_session = new TF_Session(session, graph);
    if (graph != nullptr) {
      mutex_lock l(graph->mu);
      graph->sessions[new_session] = Status::OK();
    }
    return new_session;
  } else {
    DCHECK_EQ(nullptr, session);
    return nullptr;
  }
}
```
__如上C API函数只是做了一个过渡，函数中的NewSession(opt->options, &session)才会调用后端的C++ 系统__

后端系统C++中的NewSession函数如下，这是一个全局函数，不属于哪个类，之后会调用SessionFactory类的一系列函数来进行Session的创建，这一部分的内容就属于tensorflow的核心后端部分。
```c
// tensorflow/core/common_runtime/session.cc

Status NewSession(const SessionOptions& options, Session** out_session) {
  SessionFactory* factory;
  const Status s = SessionFactory::GetFactory(options, &factory);
  if (!s.ok()) {
    *out_session = nullptr;
    LOG(ERROR) << s;
    return s;
  }
  *out_session = factory->NewSession(options);
  if (!*out_session) {
    return errors::Internal("Failed to create session.");
  }
  return Status::OK();
}
```
在C++系统中，SessionFactory根据前端传递的`Session.target`来多态创建Session对象，如DirectionSession将启动本地运行模式，而GrpcSession将启动给予RPC的分布式运行模式

![](https://upload-images.jianshu.io/upload_images/2254249-6f041f03334e53a1.png)

### 创建扩展运行graph
Python前端调用`Session.run`时，会将构造好的graph以`GraphDef`的形式发给C++，每次调用run都会将新增节点的graph发给C++后端用于extend原来的graph
![](https://upload-images.jianshu.io/upload_images/2254249-32a40ff3a1852e28.png)

后端系统每次`Session.run`执行被称为一次step， 每次step计算图会正想计算网络的输出，反向传递梯度，并完成训练参数的更新，后端系统根据`Feed`和`Fetch`对整个graph进行剪枝，得到一个最小依赖的计算子图（称为client graph）

在运行时会启动设备分配算法，如果节点之间的边横跨了设备，则将该边分裂，插入`Send`和`Recv`节点，实现通信。然后将子图片段（partition graph）注册到相应设备并启动执行。

![](https://upload-images.jianshu.io/upload_images/2254249-8e6f49ede17e91f8.png)

### 关闭和销毁Session
主动调用`sess.close`之后进行Session的关闭，关闭之后Python前端会启动GC进行垃圾回收，当`Session.__del__`被调用后，启动后台C++的Session对象销毁过程。

参考文章：
* https://www.jianshu.com/p/667cbb20d802

>声明：本文中所使用图片来源于参考文章或网络中，如有侵权，请通知将立即删除
