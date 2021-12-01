论文全称《Elfen Scheduling: Fine-Grain Principled Borrowing from Latency-Critical Workloads using Simultaneous Multithreading》，标题翻译为《Elfen调度：使用同时多线程技术从时延关键型工作负载进行细粒度原则借用》，由ANU的Xi Yang博士发表于会议ATC-2016，github上可以找到实验代码：https://github.com/yangxi/elfen

文章主要介绍了一种新的细粒度调度CPU的方法，使得对于低延迟要求的服务能够利用这些服务未执行的时候来执行系统其他普通任务，用以提高SMT同时多线程CPU的利用率。

## Abstract 摘要
摘要部分说明了Web服务器的一个现状，对于`tail latency`要求较高的一些服务如游戏或股票等会关闭同时多线程（SMT），在一个核上只运行一个服务，使得CPU的利用率很低。所以就希望能够同时运行批处理任务和时延关键型请求来利用SMT的多个硬件环境（论文中称为lanes，也就是通道），但是如果完全共享CPU资源的话又会对`tail latency`和违反 `SLO`（Service Level Objectives即服务水平目标）产生非线性的影响。

注：这里解释一下`tail latency`，也就是尾延迟，华盛顿大学的Jialin Li等人经过研究发现，硬件， OS 本身，都可能导致尾延迟响应，例如：主机系统其他进程的影响，应用程序里线程调度，CPU功耗设计等等。参看博客： http://blog.csdn.net/guo_jia_liang/article/details/53741775

注：对于`tail latency`的改善，貌似Google的Heracles的目标也和本文Elfen Scheduling相同，也是在保证满足低延迟的情况下尽可能多的利用CPU，参看Google的文章[《Improving Resource Efficiency at Scale with Heracles》](https://research.google.com/pubs/pub45351.html)，__yangxi博士在后面的introduction中提到了这篇文章，说是只是在宏观层面进行了优化，并没有通过细粒度的监测来利用SMT__

`Elfen Scheduling`论文的方式是让批处理线程来原则性借用`（principled borrowing）` SMT的硬件资源，当伙伴通道没有`latency-critical` 的线程时就让一个批处理线程在SMT的保留通道执行。让批处理线程能够快速检测出伙伴通道是否有请求，若有就立即撤出并立即归还借用的资源。论文实验中引入了一个系统调用`nanonap`

文中测试采用的 `Apache Lucene` 搜索引擎，并且论文介绍了多种策略，仅仅是采用保守策略，也就是只有当请求通道为空闲时才让批处理线程来执行就能提高利用率90%到25%，并且满足 `request SLOs`。

## Introduction 介绍
在高度工程化的系统中满足`SLOs`并不容易，因为`requests`通常具有不同的计算需求并且负载是不可预测而且突变的，所以最保守的solution就是过量提供计算资源。当争用共享资源的时候在 `chip multiprocessors`(CMPs)和SMT中就会产生干扰。文中介绍了下之前的其他人在这方面的工作，并指出它们都缺少动态机制来监测和控制在SMT上的低延迟批处理工作负载。

然后重点提出这个research就是利用SMT资源来增加利用率并不影响 `SLOs`， 利用 `principled borrowing`来动态识别空闲cycles并借用资源。借用过程实现是在ELFEN调度器中，它让批处理线程和时延关键型请求同时运行，并满足SLOs。 __首先的工作是要表明时延关键型工作负载会产生很多很短的空闲片段，这个结果会证明这是在OS级别的调度是不够的，催生了细粒度的机制。__

ELFEN引入了一种来监测和控制线程执行的机制，包括一个监测和调度在SMT不同lanes（硬件上下文）上的线程。 对于一个N路的SMT，ELFEN将时延关键型请求固定到一个通道（lane）上，将其他的批处理线程放到其它的N-1个通道上。批处理线程中有一个用于监测时延关键型请求通道，并控制所有批处理线程的执行。作者引入了一个新的系统调用`nanonap`，可以避免争用并调用`mwait`来快速释放硬件资源，在大约3000个cycles以内，这个机制提供了其它如：`yielding busy-waiting futex`都不能提供的semantics。当`nanonap`被调用时，__这个batch thread就保持在这个内核状态并不使用微内核资源，直到下一个中断或请求通道空闲__。由于批处理线程一直在OS的控制之下，所以其可能会被OS争用，ELFEN利用的共享系统状态已经能够被应用到同一核心的应用程序上了，并且没有暴露额外信息给一起运行的线程。

调度和采样机制在编译时被注入批处理应用程序，也可以用二进制re-writer程序来完成。采样系统会通过一个共享内存位置来频繁检查是否由requests，当有request的时批处理线程立刻调用`nanonap` 来释放硬件资源，以确保核心一直运转，但是这种方式只是一次利用了SMT的一个通道。另一种更激进的策略是给batch thread一个限制预算（budget），使得两个通道都能被使用，这个budget跟__SLOs、批处理线程的影响、请求队列的长度__有关。这些策略通过不同的方式来细粒度采样监测请求。

ELFEN通过编译实现于Linux kernel，self-schedules的批处理工作负载使用C和Java应用程序，时延关键型请求使用Lucene，在两路SMT一个核上实验时，`borrow idle policy`达到了峰值利用率，并且对Lucene的99%的延迟SLO没有影响。相对于只有Lucene requests，ELFEN使得核心利用率在第负载时提高了90%，在高负载时提高了25%。有一个通道一直繁忙，一直接近100%的核心利用率。

综上所述，ELFEN这篇论文的贡献：
* 分析了时延关键型工作负载没有完全利用硬件资源，空闲区间的可能性
* `nanonap`，用于细粒度线程控制的系统调用
* ELFEN，借用空闲区间的SMT资源并保证对时延关键型请求没有影响
* 各种调度策略
* 对ELFEN调度的评估
* github开源实现

## ELFEN Design and Implementation

在SMT硬件上的干扰会导致违反低延迟服务水平目标，ELFEN通过控制批处理线程的执行来限制它们对尾延迟的影响，可以通过消除干扰或者限制批处理程序的执行来达到这种目标。最简单的策略就是当有请求出现需要执行的时候强制让批处理线程放弃其通道资源，更激进的方式是通过一种预算让批处理线程和请求的处理重叠执行。ELFEN的设计采用了 两种思路，一是使用高频、低能耗的监控来寻找可供调度的区间，二是使用低延迟的调度来利用这些区间来执行批处理程序。批处理负载在编译的时候加入监控和自我调度的实现，对于最简单的borrow-idle策略来调度不需要修改低延迟工作负载，而对于更激进的策略则需要其通过共享内存暴露出请求队列的长度和最近的请求的标志，批处理线程利用`nanonap`系统调用来迅速释放硬件资源，但是并没有放弃它们的SMT硬件上下文。ELFEN调度的测试环境包括一个低延迟的请求工作负载和多个批处理负载，实现策略是通过 `setaffinity()`函数来强制将所有的请求线程绑定到对应的请求通道，将批处理线程绑定到其伙伴批处理通道。 OS 可以调度执行批处理线程，而每个批处理线程都会进行监控和我调度的过程中。

### Nanonap

系统调用 `nanonap` 被设计用来监控和细粒度的调度线程，其关键作用就是让硬件上下文进入睡眠状态而不用把硬件资源释放给OS调度器，已有的很多机制包括 mwait，WRLOS和hotplug都没有满足这个要求。mwait指令能够低延迟地释放一个硬件上下文的资源，这个指令在SPARC机器中是用户指令，而在x86中则是特权指令。IBM的PowerEN用户级的WRLOS指令有着类似的语义。指令mwait的调用通常会成对的使用要给monitor指令来确定一个mwait监控的内存地址。OS或其他的线程通过向监控的内存地址写入信息或发送一个中断来唤醒睡眠的线程。Linux调度器使用mwait来降低能耗，Linux通过为每个核心指派一个特权闲置任务，这些闲置任务会调用mwait来释放资源，将硬件置于一种低功耗的状态。简单的在用户空间建立上述的机制不能满足我们的要求，因为OS很可能调度其它准备线程到释放叼的硬件上下文。相对应的，由于抢占被关闭，nanonap会确保没有其它的线程能够在该通道上执行，并将所有的硬件资源释放给它的伙伴通道。另一个可能有效但实际没用的机制是hotplug，它能够禁止任何任务在指定的SMT通道上执行，操作系统首先关中断，然后将该通道中所有的线程都挪到其它的核心中，并将该通道切换到一个会调用idle任务。当hotplug将线程都挪到其它核心的时候，用户态调用项futex这样的指令来yield这个通道会让其它的线程在这个通道中执行。因此，无论是hotplug接口还是用户态的锁定或者mwait的调用都被设计用来相互之间释放和获取SMT通道资源，因为线程在暂停的时候不能保存对通道的独占权。

系统调用nanonap被设计用来直接控制SMT的微架构硬件资源，任何想要释放一个通道的应用程序都会调用nanonap，其会进入内核，关闭抢占(preemption)，然后睡在每个CPU的nanonap标志上。从内核的角度nanonap就是一个普通的系统调用并且其将线程视作仍在执行。因为nanonap没有关中断并且内核也没有抢占调用nanonap的线程，SMT通道会处于一种低功耗的睡眠状态直到OS通过一个中断或ELFEN调度器设置nanonap标志来唤醒该线程。在SMT通道被唤醒之后，其打开抢占并从系统调用返回。在实现中nanonap采用一个虚拟设备/dev/nanonap并使用Linux的ioctl接口来处理该设备。

```c++
/******************* USER *********************/
void nanonap() {
	ioctl(/dev/nanonap);
}
/******************* KERNEL *******************/
nanonap virtual device: /dev/nanonap;
per_cpu_variable: nap_flag;
ioctl(/dev/nanonap) {
    disable_preemption();
    my_nap_flag = this_cpu_flag(nap_flag);
    monitor(my_nap_flag);
    mwait();
    enable_preemption();
}
```

#### No starvation or new security state

Nanonap系统调用和请求通道的监控不会造成饥饿或安全问题，不会造成饥饿是因为nanonap没有关闭中断，调度器可能唤醒任意睡眠状态的线程并在时间片结束的时候在通道上调度一个不同的批处理线程。当一个批处理线程被唤醒或者一个新的线程开始执行的时候，会测试其伙伴请求通道是否存在任务，如果存在的话批处理线程就将自己置于睡眠状态。因为OS给等待nanonap的批处理线程一定的时间片，用户程序不可能通过不断的调用nanonap来执行拒绝服务攻击，因为在线程时间片用完之后OS会调度其它的线程。

ELFEN通过监控系统状态来进行决策，它读取内存和能够表明该核心是否有多个线程执行的性能计数器。所有这种系统状态足够用于同一个核心上的线程，ELFEN不会给同时执行的线程展示其它额外的信息。

#### Continuous Monitoring and Signaling

Nanonap能够让线程快速的睡眠和唤醒，而调度器还需要什么时候调用nanonap。SHIM的功能就是能够进行细粒度的监测，其将时变的软硬件时间视作连续的‘信号’。不同于很多采样工具使用中断来监测请求线程，这里的批处理线程可以连续的从内存位置和硬件性能计数器读取信号来监测请求线程。最简单的情况下就是SHIM监测请求线程是否执行。

### ELFEN Scheduling

ELFEN调度器包括多种调度策略来在满足SLOs的情况下借用未被完全利用的硬件资源。

#### Borrowing Idle Cycles

这种调度方式只在低延迟工作负载空闲的时候才执行批处理线程，当有一个请求开始执行的时候，批处理线程马上睡眠并释放硬件资源给低延迟请求线程。当请求通道空闲的时候，批处理线程被唤醒并在批处理通道执行。在实现中增加一个cpu_task_map来将一个通道的标志映射到当前正在执行的任务。每次在task_switch_to()中进行上下文切换的时候OS就更新或者map，通过观测这个信号，调度器知道哪个线程在SMT的通道中执行。每次检查时调度器查看是否时idle_task进程在请求通道执行，如果请求通道是空闲的，调度器或者执行在该通道中的批处理线程或者启动一个批处理线程。当请求通道被占的时候，调度器马上用nanonap强制让批处理线程进入睡眠状态。

```c++
/******************* KERNEL *******************/
/* maps lane IDs to the running task */
exposed SHIM signal: cpu_task_map

task_switch(task T) { cpu_task_map[thiscpu] = T; }
idle_task() { // wake up any waiting batch thread
    update_nap_flag_of_partner_lane();
    ......
    mwait();
}
/**************** BATCH TASKS *****************/
/* fast path check injected into method body */
check:
if (!request_lane_idle) slow_path();

slow_path() { nanonap(); }
```
