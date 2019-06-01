Tensorflow 是由谷歌开源的人工智能学习系统，Tensor意即张量表示多维数组，flow意味着基于数据流图的计算，支持异构设备分布式计算，它能够在各个平台上自动运行模型，从手机、单个CPU / GPU到成百上千GPU卡组成的分布式系统。TensorFlow支持CNN、RNN和LSTM算法，可应用于语音识别，自然语言理解，计算机视觉，广告等等。tensorflow官网： https://www.tensorflow.org （可能需要VPN访问）

使用的系统: Ubuntu16.04
python版本：python2.7

中文社区介绍了多种安装方式，包括针对不同系统，使用源码或直接使用pip安装，或者使用docker。这里使用最简单的安装方式，中文社区提供了使用GPU版本的安装方式，这里暂时仅使用CPU版本的安装
```
pip install https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow-0.5.0-cp27-none-linux_x86_64.whl
```
由于访问的是谷歌的网站，所以可能需要VPN才能访问上述链接，并且安装过程中可能需要权限，需要使用sudo

## Tensorflow 基本使用

Tensorflow 使用图graph来表示计算任务，在会话Session中的上下文执行图， tensor张量表示数据，使用Variable变量来维护状态，使用feed和fetch可以为任意的操作赋值或获取数据

图中的节点称为op，一个op有多个输入tensor，多个输出tensor，图在Session里被启动之后，Session将op分发到如CPU或GPU之类的设备上进行执行

构建图第一步需要创建源op， 源op不需要任何输入，例如常量op，TensorFlow Python库中有一个默认图，可用于增加op

如下实例，创建两个常量op，分别产生两个矩阵，另一个op为一个矩阵乘法，还没有在Session中被启动，所以没有运行，这三个op都是被添加到默认图中
```python
import tensorflow as tf

matrix1 = tf.constant([[3., 3.]])
matrix2 = tf.constant([[2.],[2.]])

product = tf.matmul(matrix1, matrix2)
```
在会话中启动图, run(product) 时Session负责其所需的输入，所以会触发之前的op
```python
sess = tf.Session()
result = sess.run(product)
print result
# ==> [[ 12.]]
sess.close()
```

对于GPU，若Tensorflow 自动检测到，则其会尽可能的用第一个来操作，当然若有多个GPU，可以显示的指派

这个实例为利用变量实现一个简单的计数器

```python
state = tf.Variable(0, name="counter")

one = tf.constant(1)
new_value = tf.add(state, one)
update = tf.assign(state, new_value)

init_op = tf.initialize_all_variables()

with tf.Session() as sess:

    sess.run(init_op)

    print sess.run(state)

    for _ in range(3):
        sess.run(update)
        print sess.run(state)
```

Tensorflow提供了fetch和feed机制，fetch机制可以在一次运行时取得多个tensor

feed机制可以使用一个tensor来临时替换一个操作的输出结果，feed只在调用它的方法内有效，方法结束，feed消失，placeholder描述的只是一个占位符，并不是一个特定的值

```python
input1 = tf.placeholder(tf.types.float32)
input2 = tf.placeholder(tf.types.float32)
output = tf.mul(input1, input2)

with tf.Session() as sess:
  print sess.run([output], feed_dict={input1:[7.], input2:[2.]})
```

### 不同版本代码迁移
tensorflow官网提供了工具用于0.x版本的代码迁移到1.0的版本的API，可参考： https://www.tensorflow.org/install/migration

## Tensorflow 系统架构
tensorflow上层虽然有很多语言的调用库，主要是Python的应用，但是底层是用C/C++构建的，这样可以兼顾性能及效率。另外tensorflow还有一个重要的特性就是它是基于数据流图，可以用于大规模分布式数值计算的开源框架。

![](https://upload-images.jianshu.io/upload_images/2254249-bf86142555d23538.png)

如上图所示，最底层的包括RPC和RDMA是网络层，主要负责传递神经网络的算法参数，底层另一部分是CPU及GPU，也就是设备层负责神经网络算法中的具体运算操作。

基于网络层和设备层之上的是tensorflow的kernel， 这里包括算法的具体操作，如卷积操作和激活操作等， kernel之上又构成了Distributed master，用于构建子图，将子图切割成多个分片并分发到不同的设备上进行运算。

再上面的就是API层，C API层把tensorflow分割为前端和后端，前端提供各种语言的库，主要应用为Python，前端库基于C API触发tensorflow 后端程序运行。前端库中包括各种模型训练的函数。

### client、master和worker各组件的内部工作原理
分布式版本的tensorflow中才包括`Distributed Master`和 `Worker Service`， __而单机版本的tensorflow实现了本地的Session，通过本地进程的内部通讯实现如上功能，以下图为三者之间的关系__。

![](https://upload-images.jianshu.io/upload_images/2254249-821e1cb7f3fbb146.png)

途中所示的两个任务 `job:ps/task:0`负责参数的存储和更新，`/job:worker/task:0`负责模型的训练或推理。

### client 客户端
client基于tensorflow的编程接口来构造计算图， 主要为Python和C++ 编程接口，直到Session会话被建立tensorflow才开始工作，Session建立client和后端运行时的通道，将[`Protobuf`](https://www.ibm.com/developerworks/cn/linux/l-cn-gpb/index.html) 格式的Graph发送给 `Distributed Master`，如下为client构建了一个简单的计算graph
$$ s+=w*x+b $$
![](https://upload-images.jianshu.io/upload_images/2254249-a50313d8e5954c32.png)

### Distributed Master
当client出发Session运算的时候，master根据Session.run的Fetching参数，从计算图中反向遍历来寻找所依赖的最小子图，根据设备的情况将子图切割成多个分片，将分片派发给`Work Service`，若为本地桌面环境，则`Work Service`就启动本地子图的执行过程

同时 master 还会缓存子图分片，以便以后执行过程中重复使用，避免重复计算。在执行之前，`Distributed Master` 还会进行一系列优化，如公共表达式消除、常量折叠等，随后执行优化后的计算子图

![](https://upload-images.jianshu.io/upload_images/2254249-74be8560b321f43f.png)

### 子图分片及划分算法 和 SEND/RECV节点

![](https://upload-images.jianshu.io/upload_images/2254249-5c0b9b1d06c870c0.png)

如上划分主要是将模型参数相关的`OP`进行分组，并放置在`PS`任务上，其它的op则划分为另外一组，放置在worker任务上执行

![](https://upload-images.jianshu.io/upload_images/2254249-bd2ca0fd17a0805b.png)
当计算图的边被任务节点分割，`Distributed Master`会将该边分裂，并在两个分布式任务之间插入SEND和RECV节点，实现数据传递。随后`Distributed Master`将子图分片派发给Worker，进行执行。

### Worker Service
`Worker Service`主要处理来自master的请求，调度op的tensorflow kernel实现，执行本地子图，然后进行协调任务之间的数据通信
![](https://upload-images.jianshu.io/upload_images/2254249-cc60fb203ffdb9f7.png)

关于数据传递 `SEND/RECV` 节点，对于CPU和GPU之间的数据传输使用`cudaMemcpyAsync`，对于本地的GPU之间则使用端到端的DMA进行数据传输

参考文章：
* https://zhuanlan.zhihu.com/p/31377628
* https://www.jianshu.com/p/a5574ebcdeab

>声明：本文中所使用图片来源于参考文章或网络中，如有侵权，请通知将立即删除
