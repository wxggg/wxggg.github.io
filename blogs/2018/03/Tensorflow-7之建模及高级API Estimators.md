本文主要通过官网实例花的分类来了解tensorflow建模过程，在github上tensorflow提供了很多model模可供学习。对于花的分类实例需要安装`pandas`，这是一个Python的数据处理库，可以直接处理csv格式文件。tensorflow实现了keras机器学习库，在这个实例中也被用到。

可按如下步骤进行该实例的运行，并能看到取得了很好的分类效果，之后看看具体的建模训练及评测过程。
```shell
$pip install pandas
$git clone https://github.com/tensorflow/models
$cd models/samples/core/get_started/
$python premade_estimator.py
```

### 准备数据
本例使用的是csv格式的数据，可以使用`pandas`进行处理，如下为train的部分数据，从中可以看出来第一行主要是提供相关信息，比如数据行数等，可以在`read_csv`函数中说明header=0表示第一行为header，数据从第二行开始。
```
120,4,setosa,versicolor,virginica
6.4,2.8,5.6,2.2,2
5.0,2.3,3.3,1.0,1
4.9,2.5,4.5,1.7,2
4.9,3.1,1.5,0.1,0
5.7,3.8,1.7,0.3,0
4.4,3.2,1.3,0.2,0
...
```
数据读取时read_csv函数设置names,控制读取的数据中每一列的含义，`train_x, train_y = train, train.pop(y_name)`将数据进行区分输入的train_x和train_y，前几列为训练的x。
```python
# Fetch the data
(train_x, train_y), (test_x, test_y) = iris_data.load_data()

def load_data(y_name='Species'):
    """Returns the iris dataset as (train_x, train_y), (test_x, test_y)."""
    train_path, test_path = maybe_download()

    train = pd.read_csv(train_path, names=CSV_COLUMN_NAMES, header=0)
    train_x, train_y = train, train.pop(y_name)

    test = pd.read_csv(test_path, names=CSV_COLUMN_NAMES, header=0)
    test_x, test_y = test, test.pop(y_name)

    return (train_x, train_y), (test_x, test_y)
```
然后设置属性到my_feature_columns中，`train_x.keys()`得到的就是每一列的属性
```python
# Feature columns describe how to use the input.
my_feature_columns = []
for key in train_x.keys():
    my_feature_columns.append(tf.feature_column.numeric_column(key=key))
```

__关于 Feature Columns__

Feature Columns（特征列）其实就是用于对model输入数据的一个桥梁，比如对上面的DNNClassifier分类器而言，只需要把feature column作为参数给它就能够把数据输入，在模块`tf.feature_column`中存在很多函数可以用来创建feature columns， 比如categorical_column或者dense_column，这里使用的是numeric_column。

对于feature columns的更多信息，参考官网介绍 [feature_columns](https://www.tensorflow.org/get_started/feature_columns)

### 建立分类器
这里建立了两层深度学习层，并用estimator的DNNClassifier来初始化分类器。Estimator代表一个完整的模型，是tensorflow系统的高级API部分，其API提供方法可以训练模型、判断模型的准确性并进行预测。
```python
# Build 2 hidden layer DNN with 10, 10 units respectively.
classifier = tf.estimator.DNNClassifier(
    feature_columns=my_feature_columns,
    # Two hidden layers of 10 nodes each.
    hidden_units=[10, 10],
    # The model must choose between 3 classes.
    n_classes=3)
```

__关于Estimators__

基于estimators的模型可以在本地主机或在多server的分布式环境执行，它还可以简化很多操作，比如不用建立graph等，estimators是建立在`tf.layers`上面的，所以它简化了自定义操作。

使用一个pre-made Estimators的结构
* 创建一个或多个输入函数。
* 定义模型的特征列。
* 实例化Estimator，指定特征列和各种超参数。
* 在Estimator对象上调用一个或多个方法，传递适当的输入函数作为数据源。

更多关于Estimators的信息参看官网API，[estimators](https://www.tensorflow.org/programmers_guide/estimators)

###　模型训练及评估
利用上述的分类器进行训练及评估，分别使用训练输入函数以及测试输入函数来输入数据
```python
# Train the Model.
classifier.train(
    input_fn=lambda:iris_data.train_input_fn(train_x, train_y,
                                             args.batch_size),
    steps=args.train_steps)

# Evaluate the model.
eval_result = classifier.evaluate(
    input_fn=lambda:iris_data.eval_input_fn(test_x, test_y,
                                            args.batch_size))
```
__关于dataset 数据集__

`tf.data`模块包含一系列辅助导入以及处理数据的操作，使其容易导入我们的model，主要分两个部分：读取内存中的numpy数组以及读csv文件中的行。在这个例子中，由于前期以及用`pandas`对csv文件进行了处理，所以这里是从内存中读取数组。

如下即为此例中的模型训练输入函数，可以看出其接收三个参数：特征、标签以及数据量大小。这里需要介绍一下这个slice也就是片的概念，比如对于MNIST数据，如果其shape为(60000，28，28)，那么意味着用函数`from_tensor_slices`会将其分割为60000个slices，也就是每一个为一个28x28的image。
```
def train_input_fn(features, labels, batch_size):
    """An input function for training"""
    # Convert the inputs to a Dataset.
    dataset = tf.data.Dataset.from_tensor_slices((dict(features), labels))

    # Shuffle, repeat, and batch the examples.
    dataset = dataset.shuffle(1000).repeat().batch(batch_size)

    # Return the dataset.
    return dataset
```
这里对数据进行了shuffle处理，也就是改变输入的数据的次序，使得每次运行时数据的先后顺序是不一样的，对于dataset数据集的更多信息参考官网 [datasets_quickstart](https://www.tensorflow.org/get_started/datasets_quickstart)，包括对于csv文件用dataset进行读取处理

### 预测
训练完模型之后就可以进行预测了，准备要预测的数据
```python
predictions = classifier.predict(
    input_fn=lambda:iris_data.eval_input_fn(predict_x,
                                            labels=None,
                                            batch_size=args.batch_size))
```
可以通过程序执行的INFO看一下整个执行过程
```
INFO:tensorflow:Using default config.
WARNING:tensorflow:Using temporary folder as model directory: /tmp/tmpd7x0Tz
INFO:tensorflow:Using config: {'_save_checkpoints_secs': 600, '_session_config': None, '_keep_checkpoint_max': 5, '_task_type': 'worker', '_global_id_in_cluster': 0, '_is_chief': True, '_cluster_spec': <tensorflow.python.training.server_lib.ClusterSpec object at 0x7faf17cd4910>, '_evaluation_master': '','_save_checkpoints_steps': None, '_keep_checkpoint_every_n_hours': 10000, '_service': None, '_num_ps_replicas': 0, '_tf_random_seed': None, '_master': '', '_num_worker_replicas': 1, '_task_id': 0, '_log_step_count_steps': 100, '_model_dir': '/tmp/tmpd7x0Tz', '_save_summary_steps': 100}
INFO:tensorflow:Calling model_fn.
INFO:tensorflow:Done calling model_fn.
INFO:tensorflow:Create CheckpointSaverHook.
INFO:tensorflow:Graph was finalized.
INFO:tensorflow:Running local_init_op.
INFO:tensorflow:Done running local_init_op.
INFO:tensorflow:Saving checkpoints for 1 into /tmp/tmpd7x0Tz/model.ckpt.
INFO:tensorflow:loss = 211.62344, step = 1
INFO:tensorflow:global_step/sec: 419.024
INFO:tensorflow:loss = 21.816256, step = 101 (0.240 sec)
...
INFO:tensorflow:loss = 5.6046805, step = 901 (0.198 sec)
INFO:tensorflow:Saving checkpoints for 1000 into /tmp/tmpd7x0Tz/model.ckpt.
INFO:tensorflow:Loss for final step: 5.587057.
INFO:tensorflow:Calling model_fn.
INFO:tensorflow:Done calling model_fn.
INFO:tensorflow:Starting evaluation at 2018-03-31-06:57:14
INFO:tensorflow:Graph was finalized.
INFO:tensorflow:Restoring parameters from /tmp/tmpd7x0Tz/model.ckpt-1000
INFO:tensorflow:Running local_init_op.
INFO:tensorflow:Done running local_init_op.
INFO:tensorflow:Finished evaluation at 2018-03-31-06:57:14
INFO:tensorflow:Saving dict for global step 1000: accuracy = 0.93333334, average_loss = 0.05545785, global_step = 1000, loss = 1.6637355

Test set accuracy: 0.933

INFO:tensorflow:Calling model_fn.
INFO:tensorflow:Done calling model_fn.
INFO:tensorflow:Graph was finalized.
INFO:tensorflow:Restoring parameters from /tmp/tmpd7x0Tz/model.ckpt-1000
INFO:tensorflow:Running local_init_op.
INFO:tensorflow:Done running local_init_op.
```

__关于checkpoints__

从上面的INFO中可以看到有saving checkpoints的操作，checkpoints其实是模型在训练期间产生的版本信息，由Estimators来自动写入磁盘，写到`/tmp`目录下面，同时写入的还有`event files`，这个包含的信息可以用于Tensorboard进行可视化分析。

在DNNClassifier创建的时候可以指定模型目录如下，来保存相关文件，在分类器最开始调用train的时候就开始保存。可以设置checkpoints的频率，具体参看官网教程　[checkpoints](https://www.tensorflow.org/get_started/checkpoints)
```python
classifier = tf.estimator.DNNClassifier(
    feature_columns=my_feature_columns,
    hidden_units=[10, 10],
    n_classes=3,
    model_dir='models/iris')
```

Estimators通过函数`model_fn()`来建graph，并且利用最近保存的checkpoints保存的信息来初始化相关变量。每次调用train，evaluate或predict的时候tensorflow都会自动重建模型。
