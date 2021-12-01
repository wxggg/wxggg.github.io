计算图graph就是节点与边的集合，是一个有向无环图（DAG）按照DAG图的拓扑排序依次执行OP运算，若存在多个度为0的节点可以进行并发运算
![](https://upload-images.jianshu.io/upload_images/2254249-41f78682c2a03ef1.png)

## 计算图graph从python传到底层C++
之前提到过会话Session初始化到其父类BaseSession初始化时，若graph为空会调用默认图
```python
#tensorflow/python/client/session.py
#class BaseSession(SessionInterface):
if graph is None:
  self._graph = ops.get_default_graph()
```
之后调用`get_default_graph`函数并进一步调用`_default_graph_stack.get_default()`，而这里的`_default_graph_stack`被实例化为一个`_DefaultGraphStack`对象 `_default_graph_stack = _DefaultGraphStack()`在其父类`_DefaultStack`初始化可以看到
```python
#class _DefaultStack
def __init__(self):
  super(_DefaultStack, self).__init__()
  self._enforce_nesting = True
  self.stack = []
```
这里初始化了一个空的stack，用于存放graph，再看一下类`_DefaultGraphStack`
```python
#class _DefaultGraphStack
def __init__(self):
  super(_DefaultGraphStack, self).__init__()
  self._global_default_graph = None

def get_default(self):
  """Override that returns a global default if the stack is empty."""
  ret = super(_DefaultGraphStack, self).get_default()
  if ret is None:
    ret = self._GetGlobalDefaultGraph()
  return ret

  def _GetGlobalDefaultGraph(self):
    if self._global_default_graph is None:
      # TODO(mrry): Perhaps log that the default graph is being used, or set
      #   provide some other feedback to prevent confusion when a mixture of
      #   the global default graph and an explicit graph are combined in the
      #   same process.
      self._global_default_graph = Graph()
    return self._global_default_graph
```
这里可以很清楚的看出来default图是一个`_global_default_graph`，在初始化时被置空，并在`get_default`调用时初始化为一个Graph，并满足单例模式，即全局只有一个。

再看之前python调用swig包装层调用TF_NewSession时传入的graph参数
```python
# BaseSession __init__
self._session = tf_session.TF_NewSession(self._graph._c_graph, opts, status)
```
再往后就是TF_NewSession中的创建一个TF_Session实例，这是一个结构体，但是包含构造函数
```c
TF_Session* new_session = new TF_Session(session, graph);

struct TF_Session {
  TF_Session(tensorflow::Session* s, TF_Graph* g);

  tensorflow::Session* session;
  TF_Graph* graph;

  tensorflow::mutex mu;
  int last_num_graph_nodes;

  // NOTE(ashankar): Experimental fields to help keep the
  // buffers of a TF_Tensor pinned in device memory.
  const tensorflow::DeviceMgr* device_mgr;   // Owned by session.
  std::vector<tensorflow::Device*> devices;  // Owned by device_mgr.
};
```
值得一提的是带有`TF_`开头的应该都属于将C API的包装曾所以上述的TF_Session应该是与python中的Session对象是一一对应的，而上述提及的另一个结构体`TF_Graph`应该是与python中的graph进行对应
```c
struct TF_Graph {
  TF_Graph();

  tensorflow::mutex mu;
  tensorflow::Graph graph GUARDED_BY(mu);

  // Runs shape inference.
  tensorflow::ShapeRefiner refiner GUARDED_BY(mu);

  // Maps from name of an operation to the Node* in 'graph'.
  std::unordered_map<tensorflow::string, tensorflow::Node*> name_map
      GUARDED_BY(mu);

  tensorflow::gtl::FlatMap<TF_Session*, tensorflow::Status> sessions
      GUARDED_BY(mu);
  bool delete_requested GUARDED_BY(mu);  // set true by TF_DeleteGraph

  // Used to link graphs contained in TF_WhileParams to the parent graph that
  // will eventually contain the full while loop.
  TF_Graph* parent;
  TF_Output* parent_inputs;
};
```
从`TF_Graph`结构中可以看到，其一个成员为`tensorflow::Graph graph`，这个就是后端C++中的tensorflow命名空间的Graph类，所以这里最终利用这个包装中间层来到了C++中的Graph类
```c++
// Thread compatible but not thread safe.
class Graph {
 public:
  // Constructs a graph with a single SOURCE (always id kSourceId) and a
  // single SINK (always id kSinkId) node, and an edge from SOURCE->SINK.
  //
  // The graph can hold ops found in registry. `registry`s lifetime must be at
  // least that of the constructed graph's.
  explicit Graph(const OpRegistryInterface* registry);

  // Constructs a graph with a single SOURCE (always id kSourceId) and a
  // single SINK (always id kSinkId) node, and an edge from SOURCE->SINK.
  //
  // The graph can hold ops found in `flib_def`. Unlike the constructor taking
  // an OpRegistryInterface, this constructor copies the function definitions in
  // `flib_def` so its lifetime may be shorter than that of the graph's. The
  // OpRegistryInterface backing `flib_def` must still have the lifetime of the
  // graph though.
  explicit Graph(const FunctionLibraryDefinition& flib_def);

  ~Graph();

  static const int kControlSlot;

  // The GraphDef version range of this graph (see graph.proto).
  const VersionDef& versions() const;
  void set_versions(const VersionDef& versions);

  // Adds a new node to this graph, and returns it. Infers the Op and
  // input/output types for the node. *this owns the returned instance.
  // Returns nullptr and sets *status on error.
  Node* AddNode(const NodeDef& node_def, Status* status);

  // ...
```
C++的Graph类中还包括添加边添加节点等各种操作，对于计算图graph的初始化过程从python到底层C++大概就是这么个过程。

当图为空时只有两个节点source和sink，可以确保图执行时起于source并终于sink节点
![](https://upload-images.jianshu.io/upload_images/2254249-a76cc4b63190b851.png)

## 计算图中边和节点的特征
边Edge含义前驱节点和后驱节点，边上的数据以张量Tensor的形式传递，Tensor的标识由源节点的名称和src_output唯一确定，即`tensor_id = op_name:src_output`

`src_output`表示该边是前驱节点的第`src_output`条输出边，而`dst_input`表示该边为后驱节点的第条输入边
![](https://upload-images.jianshu.io/upload_images/2254249-221ce27609548c03.png)

例如两个前驱节点和两个后驱节点，均存在两条输入边
![](https://upload-images.jianshu.io/upload_images/2254249-650717a2707fbe5f.png)

__控制依赖__ 是边中比较特殊的一种，普通的边是用于承载Tensor的，通常用实线表示，而控制依赖表示节点的执行顺序，常用虚线，

对于节点而言，`Node`持有多条输入输出的边，分别使用in_edges和out_edges表示，另外还有两个特征`NodeDef`和`OpDef`，前者持有设备分配的信息，以及OP的属性集合，而后者持有OP的元数据
![](https://upload-images.jianshu.io/upload_images/2254249-d172ea69b823e1c3.png)

最后看一下tensorflow计算图的一个实例

![](https://upload-images.jianshu.io/upload_images/2254249-df4d260996bac03c.gif)


前面介绍了下tensorflow中会话和计算图在前后端的穿插过程，图graph中比较关键的部分是变量以及OP，以手写数字识别的代码为例，这里的x,W,b均是变量，而y为一个操作过程，也就是OP
```python
x = tf.placeholder("float", [None, 784])

W = tf.Variable(tf.zeros([784, 10]))
b = tf.Variable(tf.zeros([10]))

y = tf.nn.softmax(tf.matmul(x, W)+b)
init = tf.initialize_all_variables()
```

这里的Variable其实是一个特殊的OP，拥有状态，变量初始化需要使用如上的`initialize_all_variables()`函数，如上代码为线性模型，其实际计算图可能为如下：
![](https://upload-images.jianshu.io/upload_images/2254249-61521a9db69ccf75.png)

## Variable初始化过程
Variable的调用起于python上层库，在`tensorflow/python/ops/variables.py`，Variable在使用进行OP时前必须显示的初始化，对x的赋值只是一个assign指派，实际的初始化需要考虑`initialize_all_variables()`函数，这个函数同样也在上述文件中。在安装的tensorflow文件和tensorflow源文件中这variables.py貌似不相同，这里参看安装的tensorflow库中的文件
```python
def initialize_all_variables():
  return initialize_variables(all_variables())

def all_variables():
  """Returns all variables collected in the graph.

  The `Variable()` constructor automatically adds new variables to the graph
  collection `GraphKeys.VARIABLES`. This convenience function returns the
  contents of that collection.

  Returns:
    A list of `Variable` objects.
  """
  return ops.get_collection(ops.GraphKeys.VARIABLES)

def initialize_variables(var_list, name="init"):
  """Returns an Op that initializes a list of variables.

  After you launch the graph in a session, you can run the returned Op to
  initialize all the variables in `var_list`. This Op runs all the
  initializers of the variables in `var_list` in parallel.

  Calling `initialize_variables()` is equivalent to passing the list of
  initializers to `Group()`.

  If `var_list` is empty, however, the function still returns an Op that can
  be run. That Op just has no effect.

  Args:
    var_list: List of `Variable` objects to initialize.
    name: Optional name for the returned operation.

  Returns:
    An Op that run the initializers of all the specified variables.
  """
  if var_list:
    return control_flow_ops.group(
        *[v.initializer for v in var_list], name=name)
  return control_flow_ops.no_op(name=name)
```
最后调用Variable自身的initializer函数进行初始化，这是一个OP，这个OP本质上就是一个assign操作
```python
def __init__(self, initial_value, trainable=True, collections=None,
             validate_shape=True, name=None):
    # ...
    with ops.device(self._variable.device):
      self._initializer_op = state_ops.assign(self._variable, self._initial_value).op
    # ...

def initializer(self):
  return self._initializer_op
```
回到Variable的初始化过程，对于W的初始化，`tf.zeros([784,10])`通常被称为初始值，通过assign将W内部的Tensor以引用的形式进行修改为该初始值，另外一个操作是Identity，这个可以用于读取Variable的值
![](https://upload-images.jianshu.io/upload_images/2254249-7c2cd1ef175994b6.png)

### Variable之间的依赖关系
当一个变量初始化时需要另一个变量的值时，需要用initialized_value进行指定，实际上这两个是通过Identity进行衔接，这样就可以保证W会在V之前进行初始化，这里存在两个Identity，分别进行初始化和变量读，而Identity和assign之间增加的边为控制依赖，确保了初始化的先后顺序
```python
W = tf.Variable(tf.zeros([784,10]), name='W')
V = tf.Variable(W.initialized_value(), name='V')
```
![](https://upload-images.jianshu.io/upload_images/2254249-07fcc971de877958.png)

## tensorflow中OP的本质
之前提到的的assign操作存在于文件`gen_state_ops.py`中，这是一个自动生成的文件，应该也是swig进行包装底层时产生的中间层，同样的操作还包括，assign_add,assign_sub等，它们都能够操作Variable。
```python
def assign(ref, value, validate_shape=None, use_locking=None, name=None):
  return _op_def_lib.apply_op("Assign", ref=ref, value=value,
                              validate_shape=validate_shape,
                              use_locking=use_locking, name=name)

def _InitOpDefLibrary():
  op_list = op_def_pb2.OpList()
  text_format.Merge(_InitOpDefLibrary.op_list_ascii, op_list)
  op_def_registry.register_op_list(op_list)
  op_def_lib = op_def_library.OpDefLibrary()
  op_def_lib.add_op_list(op_list)
  return op_def_lib

_op_def_lib = _InitOpDefLibrary()
```
这里有一个全局变量`_op_def_lib`，所有的op都由它进行操作，类`OpDefLibrary()`的定义如下：
```python
# tensorflow/python/framework/op_def_library.py
class OpDefLibrary(object):
  """Holds a collection of OpDefs, can add the corresponding Ops to a graph."""

  def __init__(self):
    self._ops = {}

  # pylint: disable=invalid-name
  def add_op(self, op_def):
    """Register an OpDef. May call apply_op with the name afterwards."""

  def apply_op(self, op_type_name, name=None, **keywords):
    # pylint: disable=g-doc-args
    """Add a node invoking a registered Op to a graph.
  # ...
```

tensorflow计算的单位就是OP，表示某种抽象的计算拥有多个输入输出，以及多个属性，输入输出都是以Tensor的形式存在，在tensorflow系统中，OP使用的数据`OpDef`是Protobuf格式，用于实现前端python和后端C++的数据交换。 Protobuf格式是Google的一种数据格式，具有轻便快速跨平台跨语言的特点。

可以在`tensorflow/core/framework/op_def.proto`中看到OpDef的定义，包括OP的名字，输入输出列表等等， 以下划线开头的OP被系统内部保留，如 `_Send`,`_Recv`,`_Source`,`_Sink`

OP的属性是固定的，但是输入却是动态的，可以是零输入输出或多输入输出，也可以是类型确定的或不确定的。

![](https://upload-images.jianshu.io/upload_images/2254249-7f9c1967e54108ef.png)

NodeDef可以通过op从OpRegistry中索引到OpDef

![](https://upload-images.jianshu.io/upload_images/2254249-e25fbf1637123cb9.png)

### 输入列表和属性值列表
`NodeDef`中的`input`成员制定节点的输入列表，input列表前面存普通边，后面保存控制依赖边，如`node:src_output`，表示一个普通边，用来承载Tensor的数据流，其中`node`是前驱节点的名称，`src_output`是前驱节点输出边的索引

又如`^node`表示该边为控制依赖边，node为前驱节点名称

在计算图构造的时候，OP的属性值就确定了，输入输出类型以及Shape等信息都存在OpDef的attr属性列表中


### OP的注册、构造及执行
OP注册在系统初始化的时候，后端系统中可以使用宏`REGISTER_OP`来注册，实际上就是将其转换成`OpDef`，OpDefBuilder通过链式调用Input, Output, Attr方法分别构造OP的输入、输出列表，及其属性列表。最后，通过调用Finalize成员函数，经过解析字符串表示，将其翻译为OpDef的内在表示，最后注册到OpRegistry之中。

例如 `REGISTER_OP("ZerosLike")`，如图为向系统注册了一个OP
![](https://upload-images.jianshu.io/upload_images/2254249-b1cffcdf5b4e6795.png)

计算图的构造过程主要就是定义`GraphDef`，在计算图执行启动时，将`GraphDef`传递给后端
```python
tensor = tf.constant([1, 2], name="n1")
zeros  = tf.zeros_like(tensor, name="n2")
```
![](https://upload-images.jianshu.io/upload_images/2254249-01ee84dc5c3d1d0c.png)

在执行时例如如果`zeros_like`输入[1,2]，经过zeros_like之后，输出为[0,0]
![](https://upload-images.jianshu.io/upload_images/2254249-5573e08da09ad3da.png)
