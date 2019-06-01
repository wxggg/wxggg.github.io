本例主要测试不同的统计学习方法对于mnist手写数字识别的应用，包括机器学习方法和深度学习神经网络的方法，主要应用了机器学习框架sklearn和深度学习框架tensorflow，暂时使用如下方法进行测试
* 朴素贝叶斯-sklearn
* logistic回归-sklearn
* 单层神经网络-softmax全连接-tensorflow

## 数据集简介
mnist的数据为灰度图片，分为训练数据和测试数据，数据的形式比较简单，数据标签为0-9之间的数字，mnist的数据可以使用多种方式获得，这里直接采用tensorflow的keras框架api来获取
```python
mnist = tf.keras.datasets.mnist.load_data()
```
![](http://www.sharix.site/static/img/tensorflow/tensorflow2_0.png)

用tf.keras获取的数据每一个数据实际上是28x28的图片，对应的标签为对应的数字，在机器学习方法或深度学习方法中可能要进行数据的转换，将28x28的图片数据转为1x784的线性数据，将对应的数字标签也使用如下的onehot的向量进行表示。

![](http://www.sharix.site/static/img/tensorflow/tensorflow2_0_1.png)

对于数据的处理，除了进行向量化在使用线性拟合的方式如softmax回归时还需要进行归一化，因为像素点的值为0-255之间的灰度值
```python
train_x, train_y = mnist[0][0].astype('float32')/255, mnist[0][1]
onehot_train_y = []
for ty in train_y:
    onehot = [0]*10
    onehot[ty] = 1
    onehot_train_y.append(onehot)
```



## 朴素贝叶斯分类-sklearn
朴素贝叶斯主要过程是利用标注数据进行监督学习，学习X和Y的联合概率分布，然后据此来推断预测数据为条件概率最大的类别。这里根据每个像素的值进行区分为0或者非0，作为朴素贝叶斯分类器的特征。朴素贝叶斯是一种基于概率理论的分类算法，特征之间进行条件独立性假设。

补充两个名词说明，MLE为最大似然估计，MAP为最大后验概率

使用机器学习库sklearn进行测试，分别使用GaussianNB、MultinomialNB和BernoulliNB进行测试，得到如下结果，可以看到后两者的效果比较好，并且在准确率和所须时间方面各有千秋。另外我用自己写的NB也进行了测试，由于在保存权重时使用的是dict，所以导致大量数据同时预测时速度较慢，用时达到了19s，但是正确率还行达到了0.83，如果用array来保存并计算的话应该会快很多。
```python
""" use Gaussian Naive Bayes
    accuracy: 0.55, time 1.9s    bad """
# gnb = GaussianNB()
# gnb.fit(train_linear_x, train_y)
# y_pred = gnb.predict(test_linear_x)

""" use MultinomialNB NB
    accuracy: 0.83 time 0.4s    nice! """
# mbn = MultinomialNB()
# mbn.fit(train_linear_x, train_y)
# y_pred = mbn.predict(test_linear_x)

""" use Bernoulli Naive Bayes
    accuracy: 0.84 time 0.7s    nice! """
bnb = BernoulliNB()
bnb.fit(train_linear_x, train_y)
y_pred = bnb.predict(test_linear_x)
```

## logistic回归分类-sklearn
逻辑回归其实就相当与一个单层的人工神经网络，在多分类算法训练过程中有两种方式，一种是 one-vs-rest，也就是当前类为正样本时其它全部为负样本，另一种方式是使用 multinomial，也就是多项的意思，这种方式的训练只支持lbfgs,sag和newton-cg

sklean的逻辑回归包括两种，一个是LogisticRegression，另一个是LogisticRegressionCV，后面的CV表示crossvalidation即交叉验证的意思，这两种都可以设置正则化参数L1或L2，默认为L2。这里分别使用这两种方式测试，由于我们的样本数量比较大，为6000个slice，所以可以将迭代的次数设置得小一点，不然的话训练所需的时间特别多，而且随着迭代次数的增加，貌似训练时间是非线性增加的(手动黑人问号脸)

```python
""" use LogisticRegression
    iter=20     train time = 220.492734 logistic score 0.918800
    iter=10     train time = 38.447340  logistic score 0.917500
    iter=5      train time = 13.598632  logistic score 0.903200
    iter=4      train time = 10.745325  logistic score 0.886800
    iter=3      train time = 8.031269   logistic score 0.852800
"""
logistic = linear_model.LogisticRegression(max_iter=20)
logistic.fit(train_linear_x, train_y)
logistic.score(test_linear_x, test_y)
```
使用LogisticRegressionCV训练时，由于需要交叉验证所以运算量过大，所需时间过长所以并不适用。

## 单层神经网络-softmax全连接

线性分类的方式采用的是对每一个像素点赋予一个权重，然后通过训练求得权重矩阵，这里采用的是softmax回归，与logistic回归差不多，主要区别是对于K分类就有K个权重W，而logistic回归只需要K-1个权重W。

softmax回归与logistic一样，都可以看做是一层单层神经网络，一般作为神经网络中的全连接层，这里softmax的作用就是在最后对所有结果的概率进行一个归一化。

$$
S_i = \frac{e^{z_i}}{\sum_j e^{z_i}}
$$

需要注意的是如下代码中其实主要是对W和b进行训练，因此初始时可以将其设为任意值。这里为训练过程指定的最小化误差用的损失函数为目标类别和预测类别的交叉熵，关于交叉熵，简单的理解就是用来衡量在给定的真实分布下，使用非真实分布所指定的策略消除系统的不确定性所需付出的努力的大小，具体可参考知乎问题

[如何通俗的解释交叉熵与相对熵?](https://www.zhihu.com/question/41252833)

```python
x_image = tf.placeholder("float", [None, 28,28])
x = tf.reshape(x_image, [-1,784])

W = tf.Variable(tf.zeros([784, 10]))
b = tf.Variable(tf.zeros([10]))

y = tf.nn.softmax(tf.matmul(x, W)+b)
y_ = tf.placeholder("float", [None, 10])

cross_entropy = -1 * tf.reduce_sum(y_*tf.log(y))
train_step = tf.train.GradientDescentOptimizer(0.01).minimize(cross_entropy)

for i in range(iteration):
    for j in range(num_batchs):
        batch_xs, batch_ys = train_x[100*j:100*(j+1)], onehot_train_y[100*j:100*(j+1)]
        sess.run(train_step, feed_dict={x_image: batch_xs, y_: batch_ys})
```
这里我将训练的模型的权重进行了图形化显示，如下为单条线性显示，表示了每个像素点的权重
![](http://www.sharix.site/static/img/tensorflow/tensorflow2_1.png)

如下为将对应点的像素权重组成相应的图形的结果，可以看到学习到的最终的模型
![](http://www.sharix.site/static/img/tensorflow/tensorflow2_2.png)

用这种方法预测出来的准确率大概为91%左右，[MNIST线性分类及可视化代码](https://github.com/sharixos/sharix-ml/blob/master/mnist/linear.py)
