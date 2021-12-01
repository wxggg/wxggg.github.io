信号是类Unix系统中一种常用的IPC机制，信号是发送到进程或同一进程内的特定线程的异步通知，以便通知它发生的事件。当信号发出时，操作系统会终端目标进程的执行流来传递信号，任何非原子的执行过程都可以被中断，如果进程之前已经注册过信号处理函数，该处理函数就会被调用，否则会执行默认的信号处理函数。信号和中断类似，区别是中断是由硬件调停并由内核处理，而信号是由内核调停而由进程处理。内核可能将某些中断当作信号传给进程，比如 SIGSEGV、SIGBUS、SIGILL以及SIGFPE等。

* 当其它进程调用像 `kill` 这样的函数时
* 使用 `abort` 之类的函数从进程自身发送信号
* 子进程退出时操作系统发送 SIGCHLD 信号
* 父进程死亡或在控制终端监测到挂起时发送 SIGHUP 信号
* 用户从键盘中断程序时发送 SIGINT 信号
* 当程序行为不正确时发送 SIGILL、SIGFPE和 SIGSEGV 之一
* 当程序访问 `mmap` 映射的但是不可用的内存时
* 当使用 `write` 或其他函数发送数据但是没有对象来接收数据时 SIGPIPE 信号会出现。这些函数不仅可以以错误退出并设置 `errno` 变量，还会传递 SIGPIPE 信号给程序。例如当写入标准输出并使用管道序列重定向输出到另一个程序时，如果这个程序退出了而当前程序仍在尝试发送数据就会收到 SIGPIPE 信号。除了正常函数退出返回错误，还使用了信号，因为事件是异步的，所以不能确定到底由多少数据被成功发送。在发送数据给socket的时候也会出现这种情况，这是因为数据通过线路被缓冲并发送，因此不会立即传送到目标，而OS可以实现在发送程序退出后无法传送

对于信号的处理，传统的 `signal()` 函数被弃用，推荐的方式是使用 `sigaction` 来进行处理，对应一个函数和一个struct

```c
int sigaction (int signum, const struct sigaction *act, struct sigaction *oldact);

struct sigaction {
        void     (*sa_handler)(int);
        void     (*sa_sigaction)(int, siginfo_t *, void *);
        sigset_t   sa_mask;
        int        sa_flags;
        void     (*sa_restorer)(void);
};
```

其中 `sa_handler` 为信号处理函数指针， `sa_sigaction` 提供了一种可选的信号处理的方式，`sa_mask` 允许显示设置在执行处理函数期间被阻塞的信号，如果不适用 SA_NODEFER 标志则触发的信号也会被阻塞。`sa_flags` 允许修改信号处理进程的行为。

如下为信号处理的例子，这个程序功能是程序接收到 SIGTERM 信号时退出，其中handler函数在收到信号时被调用，将 exit_flag 设置为1，然后程序退出while 循环。

```c
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>

static int exit_flag = 0;

static void handler(int sig)
{
	exit_flag = 1;
	printf("handler called\n");
}

int main(int argc, char *argv[])
{
	struct sigaction act;

	memset(&act, '\0', sizeof(act));
	act.sa_handler = &handler;
	if (sigaction(SIGTERM, &act, NULL) < 0)
	{
		perror("sigaction");
		return 1;
	}

	while (!exit_flag)
		;

	return 0;
}
```

一般情况下使用 `gcc x.c` 不进行优化来直接编译该程序，然后执行 `./a.out` ，再执行 `kill -TERM _xpid` 来发送 TERM信号给该进程，这样不会出现问题，程序在收到TERM信号之后就退出了。而如果使用 `gcc -O3 x.c` 来使用编译优化时，同样执行上述步骤程序不会退出，虽然信号处理函数仍然被调用了，因为编译器在优化过程中会将 exit_flag 变量加载进寄存器中，而不是从内存读取，所以就算信号处理函数修改了该值，while循环中访问的是寄存器的值并没还有改变，所以程序没有退出。在使用的过程中使用 `volatile` 关键字就可以解决了。

```c
static volatile int exit_flag = 0;
```

数据类型 `sig_atomic_t` 被定义用来保证信号处理和使用它的代码能够原子的进行读写。但是它并不是像 互斥锁 一样工作，比如如下的操作是不安全的，因为 `if` 操作执行了读和更新操作，但是只有单个的读和单个的写是原子的。因此在多线程程序中使用 `sig_atomic_t` 类型时仍然需要加锁，

```c
sig_atomic_t i = 0;
 
void sig_handler (int sig)
{
	if (i++ == 5) {
		// ...
	}
}
```

如果数据被修改或在信号处理程序中读取，如果仅在信号被阻塞的部分发生，则无需担心是否修改或读取了程序中的数据。但仍然需要 `volatile` 关键字。

程序接收到信号的时候是被中断的，而这个中断不知道在合适何处发生，所以在信号处理函数中应该进尽可能的使用安全的函数（signal-safe）。能够在信号处理函数中安全使用的函数列表并不是很多，包括如 `waitpid` 和 `wait` 函数来清理退出的子进程信号 SIGCHLD等。

#### 使用 signalfd() 来处理信号

`signalfd` 是一个较新的Linux接口用来处理信号，允许使用文件描述符来接收信号，这样就可以同步的进行信号处理， 使用例子可以看 [signalfd](http://www.linuxprogrammingblog.com/code-examples/signalfd)。

使用 `signalfd` 之前需要使用 `sigprocmask` 来阻塞想要处理的信号，然后调用 `signalfd` 函数会创建一个用来读入信号的文件描述符，通过这种方式传递给进程的 SIGTERM 或者 SIGINT 等信号就不会被中断，信号处理函数也不会被调用。信号会排队，程序可以从文件描述符中获取到传递来的信号，并且需要提供足够大的缓冲来读取 `struct signalfd_siginfo` 对象，其中保存着之前提到的 `siginfo_t` 类型的信息。因为访问的是文件描述符，所以可以像操作文件描述符一样操作，也可以使用 `select` 、`poll` 等函数。

在使用 `poll` 这样的函数来处理连接的单进程服务器中使用 `signalfd` 非常方便，其简化了信号处理，因为信号描述符可以添加到 `poll` 的描述符数组中，并像其他描述符一样操作，而不需要异步操作，程序不会被中断。

#### 进程收到信号时的操作

对于每个信号都有一个默认的处理操作，当没有提供信号处理函数并且没有阻塞信号的时候会被执行，比如终止进程，大部分的信号都会造成进程的终止，比如 SIGTERM 、SIGQUIT、SIGPIPE、SIGUSR1等。默认操作还包括终止进程并造成代码崩溃，比如 SIGSEGV、SIGILL和SIGABRT等。少数像 SIGCHLD 这样的信号会被忽略。 SIGSTOP和SIGCOND分别造成程序的挂起和继续，比如CTRL-Z时就会发送 SIGSTOP 信号。

如果设置了信号处理函数就需要准备好有些系统调用被信号中断的情况，尽管没有设置信号处理函数也有可能被信号中断。一般来说立即返回的函数如分配一个socket的函数 `socket` 不用等待IO操作，这样的函数不会被中断。而其他的函数需要等待如网络传输、管道读取以及显示地睡眠等是有可能被中断的，如 `select` 、`read` 及 `connect` 等函数

```c
#include <unistd.h>
#include <signal.h>
#include <stdio.h>

static void handler (int sig)
{
	printf("handler called\n");
}
 
void my_sleep (int seconds)
{
        while (seconds > 0)
                seconds = sleep (seconds);
}
 
int main (int argc, char *argv[])
{
        signal (SIGTERM, handler);
 
        my_sleep (10);
 
        return 0;
}
```

对于传输数据的函数如 `recv` 、`write` 和类似的 `select` 函数可能会被信号中断，所以需要进行继续接收数据，重启 `select` 等操作，参看里子 [how to handle interruption of system calls](http://www.linuxprogrammingblog.com/code-examples/handling-interruption-of-system-calls-by-signals) 。

## 阻塞信号

有时候需要阻塞收到的信号而不是处理它们，传统的方式是使用 SIG_IGN常量作为信号处理函数，现在推荐的方式都是使用 `sigprocmask` 函数，可以查看例子

```c
/** This program blocks SIGTERM signal for 10 seconds using sigprocmask(2)
 * After that the signal is unblocked and the queued signal is handled.
 */
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int got_signal = 0;

static void hdl(int sig)
{
	got_signal = 1;
}

int main(int argc, char *argv[])
{
	sigset_t mask;
	sigset_t orig_mask;
	struct sigaction act;

	memset(&act, 0, sizeof(act));
	act.sa_handler = hdl;

	if (sigaction(SIGTERM, &act, 0))
	{
		perror("sigaction");
		return 1;
	}

	sigemptyset(&mask);
	sigaddset(&mask, SIGTERM);

	if (sigprocmask(SIG_BLOCK, &mask, &orig_mask) < 0)
	{
		perror("sigprocmask");
		return 1;
	}

	sleep(10);

	if (sigprocmask(SIG_SETMASK, &orig_mask, NULL) < 0)
	{
		perror("sigprocmask");
		return 1;
	}

	sleep(1);

	if (got_signal)
		puts("Got signal");

	return 0;
}
```

程序会睡眠并且忽略 SIGTERM 信号，因为使用了 `sigprocmask` 阻塞了该信号，该信号会在内核中排队，并在程序不阻塞该信号的时候被传递到进程中。其中 `sigset_t` 类型表示信号集合，而不是一个信号， SIG_BLOCK 参数表明这个集合中的信号全部都被阻塞，而 SIG_SETMASK 参数表示在集合中的信号被阻塞，而不在该集合中的信号就不会被阻塞，所以这里用来进行解除阻塞的操作。

#### 避免竞争条件

对于使用 `select` 和 `accept` 会产生竞争的例子：[Signal race with select() and accept()](http://www.linuxprogrammingblog.com/code-examples/signal-race-select-accept) 。这个例子使用 `select` 因为其侦听多个接口也可也等待传入连接以外的某些事件。希望能够使用SIGTERM之类的信号干净的关闭它（如删除PID文件、等待挂起的连接完成等）。为了做到这一点，定义了一个信号处理函数设置全局标志并且当信号到达的时候`select` 会被中断。如果程序执行到 `select` 的时候获得了 SIGTERM 信号，那么程序不会被中断，因为 select 会让程序睡眠直到有它监控的文件描述符准备好了。使用 `pselect` 可以改进这个程序， `select` 和 `pselect` 的区别在于后者提供了 `sigset_t` 类型的参数，这些信号的集合在系统调用的执行过程中不会被阻塞。

#### 等待信号

如果需要执行一个外部命令并等待其退出，但是又不想一直等待就可以设置一个等待时间，这个过程可以分别使用 `fork` 或 `execve` 、`sleep` 和 `sigtimedwait` 等来实现，`sigtimedwait` 能够允许程序在没有竞争的情况下等待一个信号，一个缺点是其被其它的信号中断的时候没有说明已经等待了多少时间，所以不知道什么时候重启是正确的。等待信号也可以使用如 `sigsuspend` 、`sigwaitinfo` 及 `pause` 函数等。

#### 发送信号

* 发送信号的方式包括从终端输入CTRL-C、CTRL-\及CTRL-Z，分别对应 SIGINT、SIGQUIT和SIGSTOP信号。

* 可以使用 `kill` 来通过进程pid发送信号
* 使用 `raise` 和 `abort` 可以给进程本身发送信号。
* 使用 `sigqueue` 函数可以同时发送信号和数据，类似 `kill` 但是有一个 `const union sigval` 参数可以用来发送一个整型或者指针。

#### 实时信号

POSIX定义了实时信号并且Linux也提供了支持，和标准信号的区别主要在于：

* 如果信号在发送时被阻塞，则可以将多个实时信号排队等待该过程，而标准信号只有给定类型中的一个会排队，其余的被忽略
* 实时信号的传递顺序会确保与发送顺序相同

#### 信号和进程、线程

使用 `fork` 创建子进程时信号队列是空的，尽管有些信号可能在为父进程排队。信号处理函数和阻塞信号状态会被子进程继承，与信号有关的文件描述符的属性也会被继承。

#### 参考内容
* [Linux Programming Blog / All about Linux signals](http://www.linuxprogrammingblog.com/all-about-linux-signals?page=show)