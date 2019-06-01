Tensorboard是一个用于可视化和理解tensorflow训练过程的一个web工具，可以通过保存tensorflow在训练过程中的graph的信息，然后利用tensorboard进行可视化，并在浏览器中显示出来。一般在安装tensorflow的过程中会默认安装tensorboard，可以在github上找到tensorboard的源码。

[github tensorboard](https://github.com/tensorflow/tensorboard)

![](http://www.sharix.site/static/img/tensorflow/tensorflow7_2.png)

本文主要以tensorflow提供的MNIST例子来进行了解tensorboard的使用

## tf.summary API介绍
对于tensorboard而言，用于其可视化的数据是利用tensorflow在训练过程中保存下来的一些event信息，可以利用tensorflow的`summary API`来进行收集。比如MNIST利用cnn来训练的例子，这个例子主要是训练一个卷积神经网络cnn来识别MNIST数据中的像素点，我们需要记录学习率和目标函数的变化，就可以使用`tf.summary.scalar`操作来收集信息，可以获得如`学习率`和`损失函数`等信息。

`tf.summary.histogram`可以用于收集来自特定激活(activations)的分布以及梯度或者权重的分布，
`tf.summary.merge_all`用于将summary的操作集合成一个op，用以产生summary数据，`tf.summary.FileWriter`用于将Protobuf数据写入硬盘，为了减少数据所以在每隔n步才做一次整合数据收集op。具体操作如下
```python
def variable_summaries(var):
  """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
  with tf.name_scope('summaries'):
    mean = tf.reduce_mean(var)
    tf.summary.scalar('mean', mean)
    with tf.name_scope('stddev'):
      stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
    tf.summary.scalar('stddev', stddev)
    tf.summary.scalar('max', tf.reduce_max(var))
    tf.summary.scalar('min', tf.reduce_min(var))
    tf.summary.histogram('histogram', var)
```

## MNIST训练收集summary过程
我们之前介绍的MNIST的cnn方法，采用的是两层卷积层、两层池化层以及最后一层全连接层，这一次貌似有点不同。首先看一下参数初始化过程，这里可以设置输入的数据的位置，也可以设置产生的log记录的目录，利用`argparse`进行转换，然后就是对输入的数据进行解压。
```python
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '--data_dir',
    type=str,
    default=os.path.join(os.getenv('TEST_TMPDIR', '/tmp'),
                         'tensorflow/mnist/input_data'),
    help='Directory for storing input data')
```
之后读入数据并读入数据到mnist，创建一个`InteractiveSession()`，__关于InteractiveSession()，与Session最大的区别就在于，Session需要在启动之前就构建整个计算图，而InteractiveSession()可以在运行图的时候插入一些op__，对于此例需要在训练过程中记录信息就需要插入summary的op。
```python
# Import data
mnist = input_data.read_data_sets(FLAGS.data_dir,
                                  fake_data=FLAGS.fake_data)
sess = tf.InteractiveSession()
# Create a multilayer model.
```
如下的变量创建过程也跟之前不同，这里使用了`name_scope`，意思是命名空间，目的是要区分不同的变量名，因为在整张图中很有可能会有重名的变量，所以这样可以进行区分，并且在可视化的时候这样可以更清晰。关于`name_scope`还可以参看：
* [知乎-tensorflow里面name_scope, variable_scope等如何理解？](https://www.zhihu.com/question/54513728)
* [TensorFlow入门（七） 充分理解 name / variable_scope](https://blog.csdn.net/jerr__y/article/details/70809528)
```python
# Input placeholders
with tf.name_scope('input'):
  x = tf.placeholder(tf.float32, [None, 784], name='x-input')
  y_ = tf.placeholder(tf.int64, [None], name='y-input')

with tf.name_scope('input_reshape'):
  image_shaped_input = tf.reshape(x, [-1, 28, 28, 1])
  tf.summary.image('input', image_shaped_input, 10)
```
这里解释一下这个input和input_reshape，我们知道mnist数据集是28x28的图片，输入的x是784(=28*28)，需要将其转成二维矩阵，所以输入的tensor其实是有四个维度[batch_size, image_width,image_height, channels]，也就是对应着`tf.reshape(x, [-1, 28, 28, 1])`中的第二个参数，这里的-1表示不用指定这一维度。这里的channel表示颜色信息，这里黑白就是1或0。


## 神经网络层
如下所示，此例采用函数`nn_layer`来进行每一层神经网络的初始化，其中包括对`variable`和`summary`的设置，默认采用线性整流函数relu为激活函数，
```python
def nn_layer(input_tensor, input_dim, output_dim, layer_name, act=tf.nn.relu):
  """Reusable code for making a simple neural net layer.

  It does a matrix multiply, bias add, and then uses ReLU to nonlinearize.
  It also sets up name scoping so that the resultant graph is easy to read,
  and adds a number of summary ops.
  """
  # Adding a name scope ensures logical grouping of the layers in the graph.
  with tf.name_scope(layer_name):
    # This Variable will hold the state of the weights for the layer
    with tf.name_scope('weights'):
      weights = weight_variable([input_dim, output_dim])
      variable_summaries(weights)
    with tf.name_scope('biases'):
      biases = bias_variable([output_dim])
      variable_summaries(biases)
    with tf.name_scope('Wx_plus_b'):
      preactivate = tf.matmul(input_tensor, weights) + biases
      tf.summary.histogram('pre_activations', preactivate)
    activations = act(preactivate, name='activation')
    tf.summary.histogram('activations', activations)
    return activations
```
下面看一下其中提到的summary操作，对于变量的summary操作如下，其中有一个`mean = tf.reduce_mean(var)`，这里reduce的意思其实就是降维的意思，表示在指定的维度上求平均。这里的几个scalar操作其实相当于保存了如上调用了这个函数的weight维和biases维的平均值、最小值、最大值和stddev等，这些都是针对变量也就是variable而言的。对于histogram的信息，上面神经网络层中记录了activation的信息，这里采用的激活函数是relu，对于每个变量也保存了histogram。
```python
def variable_summaries(var):
  """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
  with tf.name_scope('summaries'):
    mean = tf.reduce_mean(var)
    tf.summary.scalar('mean', mean)
    with tf.name_scope('stddev'):
      stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
    tf.summary.scalar('stddev', stddev)
    tf.summary.scalar('max', tf.reduce_max(var))
    tf.summary.scalar('min', tf.reduce_min(var))
    tf.summary.histogram('histogram', var)
```

### 第一层网络
如下为利用`nn_layer()`函数构建的第一层网络，输入x为人一个784像素点的数据，输出为500维的数据，具体来看一下在`nn_layer()`函数中的操作过程，首先创建了一个784x500的权重矩阵变量`weights`，然后创建了500维的偏差变量`biases`，然后创建了一个`W*x+b`的操作，或者说是`x*W+b`，这样对应维数才是正确的，然后将这个线性函数作为结果输入到激活函数relu中，作为一个op返回。
```python
hidden1 = nn_layer(x, 784, 500, 'layer1')
```
![](http://www.sharix.site/static/img/tensorflow/tensorflow7_3.png)

### 第二层网络
这里介绍一下`tf.nn.dropout`，这是tensorflow中用于防止或减轻过拟合而使用的函数，一般用于全连接层，其中的参数`keep_prob`就是是否保留数据的概率，这样每一个计算得到的结果都以一定的概率进行保留。

所以对于第二层网络的输入就是第一层输出的n个500维的结果，这n个结果经过一定的概率进行随机筛选为`dropped`，作为第二层网络的输入，第二层网络其实就是一个全连接层，输出为判断的10个数字。
```python
with tf.name_scope('dropout'):
  keep_prob = tf.placeholder(tf.float32)
  tf.summary.scalar('dropout_keep_probability', keep_prob)
  dropped = tf.nn.dropout(hidden1, keep_prob)

# Do not apply softmax activation yet, see below.
y = nn_layer(dropped, 500, 10, 'layer2', act=tf.identity)
```

### 训练并保存summary
最后计算交叉熵`cross_entropy`，并将减少交叉熵作为每一次训练的目标，用summary保存交叉熵和精确度，利用`tf.summary.FileWriter`来保存到文件中。
```python
with tf.name_scope('cross_entropy'):
  with tf.name_scope('total'):
    cross_entropy = tf.losses.sparse_softmax_cross_entropy(
        labels=y_, logits=y)
tf.summary.scalar('cross_entropy', cross_entropy)

with tf.name_scope('train'):
  train_step = tf.train.AdamOptimizer(FLAGS.learning_rate).minimize(
      cross_entropy)

with tf.name_scope('accuracy'):
  with tf.name_scope('correct_prediction'):
    correct_prediction = tf.equal(tf.argmax(y, 1), y_)
  with tf.name_scope('accuracy'):
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
tf.summary.scalar('accuracy', accuracy)

# Merge all the summaries and write them out to
# /tmp/tensorflow/mnist/logs/mnist_with_summaries (by default)
merged = tf.summary.merge_all()
train_writer = tf.summary.FileWriter(FLAGS.log_dir + '/train', sess.graph)
test_writer = tf.summary.FileWriter(FLAGS.log_dir + '/test')
tf.global_variables_initializer().run()
```
如下可以看到整个训练的graph
![](http://www.sharix.site/static/img/tensorflow/tensorflow7_1.png)

## TensorBoard 使用

按照如下步骤运行`mnist_with_summries.py`的程序便收集了足够的summary信息，然后启动tensorboard，在`localhost:6006`端口便可以访问，用浏览器打开即可
```python
python mnist_with_summaries.py --data_dir=MNIST_data --log_dir=MNIST_log
tensorboard --logdir=MNIST_log
```
tensorboard中提供几个方面的可视化信息，包括scalars、images、graphs、distributions和histograms。

### scalars 展示标量信息

![](http://www.sharix.site/static/img/tensorflow/tensorflow7_4.png)

上述表示准确率和交叉熵，其中横坐标为执行的步数，可以看出随着训练的步数增加，准确率在提高，而交叉熵在减小。同时也可以看出收敛速度比较慢，而且最后的准确率只有80%左右，说明只用两层神经网络没有达到很好的效果，可以加上池化层进行处理。其中红线表示训练过程，蓝线表示测试过程。

![](http://www.sharix.site/static/img/tensorflow/tensorflow7_5.png)

这个是第一层神经网络的biases的数据，也就是偏差，可以看出最大值在变大，最小值在变小，说明神经元之间的参数差异越来越大，这是我们希望得到的结果，因为不同的神经元应该去关注不同的特征，所以参数应该不同。

另外还可以看到权重矩阵weights也有着相似的变化趋势，`stddev`其实是标准差，也是反映了神经元之间的区分度。


### images 和 graphs
`images`中会显示我们开始时进行了reshape的输入数据，显示784维的点数据进行变换为28x28的图片数据，类似的若进行声音处理还会有`audio`信息

`graphs`中会显示整个图以及其中的各个节点，点开各个op节点可以看到其输入以及输出特征。

### distributions 和 histograms
`distributions` 表示的是神经元输出的分布，包括激活函数之前的分布和之后的分布。
![](http://www.sharix.site/static/img/tensorflow/tensorflow7_6.png)

`histograms`表示的是直方图，相比于`distributions`只是换了种显示方式而已。
![](http://www.sharix.site/static/img/tensorflow/tensorflow7_7.png)


最后附一篇tutorials： https://github.com/yongyehuang/Tensorflow-Tutorial
