由于作者使用的是Lucene的开源代码以及另外一个Lucene性能测试的开源项目代码，而Lucene的代码会经常更新，幸好对应的性能测试代码也会对应更新，性能测试代码： https://github.com/mikemccand/luceneutil

准备作者的ELFEN代码以及作者的Luceneutil代码，从github上可得到 https://github.com/yangxi

然后根据作者的说明进行实验,__准备实验数据__，wiki的英文数据，利用如下
```perl
# Usage
#1. Download the wikipedia data
python src/python/setup.py -download
```
__准备Lucene引擎__，clone最新的Lucene代码，并用ant编译，如下Apache的源码下载时容易掉线，用github上的镜像就不会出现下载掉线的问题

```perl
#2. Build the Lucene
"cd ../; git clone git://git.apache.org/lucene-solr.git trunk;"
"cd trunk; git checkout -b new_branch ceb66d34c0a6f840ec195f6da85e323de5e9a04d"
"cd ./lucene; ant compile-test"
```
然后设置环境变量，__编译Lucene测试代码__，准备`elfenSetting.sh`并配置，准备`setupforelfen.sh`，准备`src/main/perf/elfen_signal.c`
准备添加的Java文件，在路径`src/main/perf`下： `Affinity.java`，然后执行下面shell脚本，Lucene和luceneutil都需要使用最新的代码，不然编译可能会出错

```perl
#3. Build the searching benchmark
Please set the parameters in "./scripts/elfenSetting.sh" correctly, then execute
"./scripts/setupforelfen.sh"
```
__创建索引__，准备文件`createIndex.sh`，并执行下述过程，这个过程可能会报错，根据提示需要添加`-waitForCommit` 在`createIndex.sh`中java执行的参数中
```perl
#4. Build the index
Executing "./scripts/createIndex.sh" creates the index at INDEX_DIR. "-docCountLimit"
controls the number of wikipedia documents for indexing.
```
__启动服务__，准备文件`runSearchServer.sh`，这一步会启动不成功，报错 _argument -taskRepeatCount isn't recognized_，这是由于对于我们是以server的形式启动的服务，进入`SearchPerfTest.java`中可以查看到，对于以`server:127.0.0.1:7777`为tasksFile的方式，`-taskRepeatCount`没有被用到，因而报了参数未使用即未识别的异常。尝试将`runSearchServer.sh`中的`-taskRepeatCount 20`去除掉，同样错误还有一个`-tasksPerCat -1`，其实也可以把`SearchPerfTest.java`中参数检查调用给去除掉。
```perl
#5. Run the server
Executing "./scripts/runSearchServer.sh" launches the searching server. "-searchThreadCount"
controls the number of worker that handles searching requests.
```
__发送请求进行测试__ 通用准备文件 `./elfenDemo/send.sh` , `./scripts/sendTasks.py`和 `./scripts/parseTasks.py`，这里作者是以测试服务器的形式来测试的，即使用两台机器一台给另一台发送数据，这里我测试桌面环境的性能，就在本地单机进行测试
```perl
#6. Sending requests
Clone or copy this repository to a remote machine, then "cd ./elfenDemo; ./send.sh"
```
__请求参数__ 以如下为例可以了解测试程序的参数含义，包括任务文件，文件中包含了请求的item，然后是server的IP和端口，然后是QPS=100，也就是每秒钟发送请求为100，然后是numTasksPerCat和runTimeSec，之后是保存文件和迭代次数，以及是否对请求进行随机乱序调整
```python
python ../src/python/sendTasks.py /home/open/elfenproj/elfen/client/script/wiki.1M.nostopwords.term.tasks 127.0.0.1 7777 100 1000000 200000 test_100_20 20 s

tasksFile = sys.argv[1]
serverHost = sys.argv[2]
serverPort = int(sys.argv[3])
s = sys.argv[4]
if s == 'sweep':
  meanQPS = s
else:
  meanQPS = float(s)
numTasksPerCat = int(sys.argv[5])
runTimeSec = float(sys.argv[6])
savFile = sys.argv[7]
iteration = sys.argv[8]
randomshuffle = sys.argv[9]
```

#### 解决yangxi的测试代码与luceneutil原作者代码冲突
由于论文需要利用perf来测试其它参数如 __receiveStamp, processStamp, finishStamp, retiredIns, unhaltedCycles__ 等，所以需要对原Lucene性能测试代码进行修改

之前添加的`Affinity.java`代码，其实也是一个桥梁，用以勾通Java Lucene测试代码和`elfen_signal.c` C代码，C代码中用JNICALL来描述C函数，使得其能够被Java所调用，而C函数里面就可以直接进行性能测试perf了
```c++
package perf;
public class Affinity{
  static {
    System.loadLibrary("elfen_signal");
  }
  public static native void setCPUAffinity(int cpu);
  public static native void initPerf();

  public static native void createEvents(String[] eventNames);
  public static native void readEvents(long[] result);

  public static native void initSignal();
  public static native void postSignal(int stage, int id, int cpu);
  //  public static native void postEnqueSignal();
  //  public static native void postDequeSignal();
}
```
在`SearchPerfTest.java`中需要添加如下代码，可比照yangxi的代码和原测试作者的代码
```c++
import perf.Affinity;

Affinity.initPerf();
Affinity.initSignal();
```
#### 第一阶段测试数据结果
解决了代码版本冲突之后，可以进行测试了，这里我使用qps为100迭代30次测试初步数据，大概花了几分钟就测完了，如下为部分数据，可以看到我们测试的参数包括，任务id，totalHitCount应该是含有该请求的文档数量(?)，后面的三个stamp可用于以后处理时算运算时间及延迟时间，然后的两个参数retiredInstruction和unhaltedCycles需要使用perf组件才能测试，我们现在还没有加入perf组件所以都为0，最后一个参数为客户端的延迟
```python
#taskID->int,totalHitCount->int,receiveStamp->long,processStamp->long,finishStamp->long,retiredInstruction->long,unhaltedCycles->long,clientLatency->int
       0:  4234217:  67743401434753:  67743401539071:  67743985453207:               0:               0: 675
       1:  4440705:  67743401946212:  67743996516638:  67744243676456:               0:               0: 913
       2:  4351245:  67743402271872:  67744249068768:  67744456409962:               0:               0: 1116
       3:  3218737:  67743402625665:  67744456763834:  67744648621783:               0:               0: 1305
       4:  3528398:  67743402889552:  67744649191616:  67744868677265:               0:               0: 1518
       5:  2441864:  67743403210064:  67744869214598:  67745024909397:               0:               0: 1669
       6:  2615048:  67743403481574:  67745025286981:  67745184913768:               0:               0: 1820
       7:  2451097:  67743403810912:  67745192104370:  67745336450148:               0:               0: 1961
       8:  2498833:  67743404089783:  67745336846920:  67745460089831:               0:               0: 2089
       9:  1975468:  67743404398395:  67745470577842:  67745585326655:               0:               0: 2195
      10:  2647529:  67743414745542:  67745585709470:  67745735230796:               0:               0: 2321
```

然后是数据的解析，虽然现在还缺失上面两个参数，先对数据进行处理，看看结果
```
python ../src/python/parseTasks.py ./test_100_30
```
#### 分析一下上述解析代码的逻辑

首先看一下最后生成的qps-latency.csv文件得到的结果，可以看到我们希望测量的几个数据包括qps，实际的qps，然后就是对应的50%和95%的几个数据，暂时还不知道是什么，最后是CPU的利用率以及IPC的值，我们上面说了还没有加入perf部分，所以现在这两个也都为0，好了再看看解析程序拿到原始数据之后都做了些什么才得到最后的结果
```python
#timestamp:2018-05-06 15:05:52.509141 qps,realqps,ptime_50latency,ptime_95latency,ltime_50,ltime_95,CPU utiliztion,IPC
100,100,5.056,22.729,43.214,510.353,23031.555,25350.111,0.000,0
#budgets=(  [100]=-25250  )
#ltime_per_index=[28984, 3313, 4001] ptime_index [33665, 29691, 2294]
```

首先解析程序可以输入多个logfile，可以一起解析，并根据对应的qps调用parse_lucene_log分别解析，保存在logs[qps]中，logs为一个dict，所以这里可以看出对于同一个qps多次迭代的结果之间可能会冲突，只需要一个就够了。
```python
logs = parse_logs(sys.argv[1:])
```
然后看看parse_lucene_log到底干了啥，它的输入参数为文件名、qps和迭代次数iters，它拿到文件名之后又调用parse_log来获取数据，并保存到parsed_log字典，然后看看parse_log到底干了啥，parse_log最终才打开了logfile，它根据如下几个条目来保存对应的值，比我们测得的结果多了serverQtime:serverPtime:serverLatency这几项，这几项是在后面经过计算得到的。
```perl
hl = "#taskid:hits:receiveStamp:processStamp:finishStamp:retiredIns:retiredCycles:clienttime:serverQtime:serverPtime:serverLatency\n"
```
在parse_log中将每一列的结果都存为一个list，并把对应条目的多个list都存到cols[]中，这也是一个list，然后在raws中保存了每一行为单位的原始数据，这里顺带计算了真实的迭代次数，以及几个时间，然后将这几个计算的结果保存到`rtime.csv`中，条目为#no id clientlatency serverlatency serverPtime serverQtime。
```python
cols[key_col["clienttime"]] = np.array(cols[key_col["clienttime"]]);
cols[key_col["serverLatency"]] = (np.array(cols[key_col["finishStamp"]]) - np.array(cols[key_col["receiveStamp"]]))/(1000 * 1000)
cols[key_col["serverPtime"]] = (np.array(cols[key_col["finishStamp"]]) - np.array(cols[key_col["processStamp"]]))/(1000 * 1000)
cols[key_col["serverQtime"]] = (np.array(cols[key_col["processStamp"]]) - np.array(cols[key_col["receiveStamp"]]))/(1000 * 1000)
cpuPtime = np.array(cols[key_col["retiredCycles"]])/(2*1000*1000)
```
至此，接下来需要 __计算满足延迟小于yms所占的百分比x%__ ，首先需要对clienttime进行排序，clienttime就是logfile中的最后一列的数据，也就是client的延迟，大概看了一下，貌似开始时client延迟比较高，到比较靠后的时候比较小，好像还成一定的周期变化，可能和其它程序的运行有一定的影响。这里计算百分比采用的是前20000个结果，对client延迟排序之后每隔100个结果作为一个百分点，保存taskid为刚好在这个百分点处的任务名，保存其对应的serverlatency、serverqtime，这两个就是上面已经计算过了的。然后还要计算server的平均时间，并保存cpu的时间。cpu时间的计算如上，就是用retired周期数来表示其时间，获得这些信息之后将其保存到`./client-time-max.csv`，这里由于我们没有测cpu的周期数，所以cpu时间为0。然后计算clienttime在总的clienttime中的分布，也就是对clienttime为xms的次数为k，则其总时间x*k(ms)在总时间中所占的百分比，保存到`./client-time-dist.csv`中。并且以类似的手法保存clienttime最大的200个样本的数据保存到`./top200.csv`。
```python
#computer averageqtime
sum_server_qtime = 0;
for qindex in range(ri_base,ri_top):
    server_index = sorted_index[qindex];
    this_server_time = cols[key_col["serverQtime"]][server_index]
    sum_server_qtime += this_server_time;
avg_server_qtime = sum_server_qtime / (ri_top - ri_base);
cputime = cpuPtime[client_index];

#x is ms, y is % of requrest
f = open('./client-time-dist.csv', 'w');
client_time_freq = norfreq(client_time)
client_time_dist = norfreq_to_timefreq(client_time_freq);
```
然后回到parse_lucene_iter __计算处理时间等__，处理时间用finish_stamp_index减去process_stamp_index，然后计算其分布百分比，从收到请求到处理完的总时间用finish_stamp_index减去receive_stamp_index。利用如下函数计算处理延迟latency，将其排序之后获得前50%、95%和99%的延迟。

```python
def latency(vals):
    average_latency = np.average(vals);
    sorted_vals = sorted(enumerate(vals),key=lambda i:i[1])
#    sorted_vals = sorted(vals);
    mean_index = int(len(sorted_vals)*0.5)
    per_95_index = int(len(sorted_vals)*0.95)
    per_99_index = int(len(sorted_vals)*0.99)
    return {"avg":average_latency, "50":sorted_vals[mean_index][1], "95":sorted_vals[per_95_index][1], "99":sorted_vals[per_99_index][1], "perc_index":[sorted_vals[mean_index][0],sorted_vals[per_95_index][0],sorted_vals[per_99_index][0]]};
```
然后 __计算空闲时间__，如下利用两次开始处理的stamp的差值，？？？这里为什么是乘以2再减去cpu的运算的时钟周期呢？？？
```python
cycle_index = parsed_log["key_col"]["retiredCycles"];
instruction_index = parsed_log["key_col"]["retiredIns"];
idletimeNS = diff_cols[process_stamp_index] * 2 - diff_cols[cycle_index];
```
最后计算一下ipc
```python
ipkc = (np.array(cols[cycle_index]) * 1000)/np.array(cols[instruction_index]);
ipkc_hist = norfreq(ipkc);
ipkc_perc = latency(ipkc);
```
然后在回到parse_lucene_log中 __计算到了观测到的qps和cpu的利用率__
```python
wall_total_cycle = cols[finish_stamp_index][-1] - cols[rc_stamp_index][0];
wall_total_sec = wall_total_cycle/(1000000000);
avg_qps = nr_tasks / wall_total_sec;
# observed QPS
print "iters:%d (%d), tasks:%d, cycles:%d, qps:%f (%d)\n" % (nr_iters, expected_iter, nr_tasks, wall_total_cycle, avg_qps, expected_qps);
# CPU utilization
diff_cycle_col = parsed_log["diff_cols"][cycles_index]
nr_cycles = np.sum(diff_cycle_col);
nr_wall_cycles = cols[process_stamp_index][-1] - cols[process_stamp_index][0]
utilization = nr_cycles/(nr_wall_cycles * 2.0);
print "total cycles:%d, total wall cycles:%d, utilization:%f\n" % (nr_cycles, nr_wall_cycles * 2, utilization);
```

#### 数据结果分析
从原始数据进行解析后生成了几个文件，分别是`client-time-dist.csv`，`client-time-max.csv`，`idletime-dist.csv`，`ptime-dist.csv`，`ptime-time-dist.csv`，`qps-latency.csv`，`rtime.csv`。这些文件对应不同的信息，包括客户端的时间以及CPU的空闲时间，包括处理时间。对于论文中的图1，可以使用文件`ptime-time-dist.csv`中的数据绘图而得。

在文件`qps-latency.csv`中保存了最终的结果，可以查看对应qps的延迟，以及CPU的利用率和IPC的值，由于目前实验代码中还没有加入perf测量CPU的数据所以还没有CPU利用率和IPC的值。

#### 添加perf测量CPU利用率和IPC
查询服务程序入口在`SearchPerfTest.java`中，需要在这里就添加Affinity，
```c++
Affinity.initPerf();
Affinity.initSignal();
```
执行查询任务主要是在`TaskThread.java`中，所以也要添加`perf.Affinity`，在run函数中首先设置CPU的线程ID，并创建perf测量的各项事件。
```c++
Affinity.setCPUAffinity(threadID);
String[] eventNames = {"INSTRUCTION_RETIRED:u:k","UNHALTED_CORE_CYCLES:u:k"};
Affinity.createEvents(eventNames);

// Affinity.java
public class Affinity{
  static {
    System.loadLibrary("elfen_signal");
  }
  public static native void setCPUAffinity(int cpu);
  public static native void initPerf();

  public static native void createEvents(String[] eventNames);
  public static native void readEvents(long[] result);

  public static native void initSignal();
  public static native void postSignal(int stage, int id, int cpu);
  //  public static native void postEnqueSignal();
  //  public static native void postDequeSignal();
}
```
这里的Affinity中的函数调用的其实是elfen_signal.c中的C函数，使用loadLibrary加载C程序elfen_signal，以setCPUAffinity函数为例，其实际操作如下
```c
JNIEXPORT void Java_perf_Affinity_setCPUAffinity(JNIEnv *env, jobject obj, jint cpu)
{
  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  CPU_SET(cpu, &cpuset);
  pid_t mytid = syscall(SYS_gettid);
  /* struct sched_param new_param; */
  /* new_param.sched_priority = 98; */
  /* sched_setscheduler(mytid, SCHED_FIFO, &new_param); */

  if (pthread_setaffinity_np(pthread_self(), sizeof(cpuset), &cpuset) == -1){
    fprintf(stderr, "Failed set CPU affinity to cpu %d\n", cpu);
  }
  printf("bind thread %d to cpu %d with scheduling class %d\n", (int)mytid, cpu, sched_getscheduler(mytid));
}
```
利用perf测量CPU的利用率以及IPC就可以获取对应文中第2个图的数据，实际测量大致走势相似，随着qps的增大，负载逐渐增大导致延迟非线性增加。
