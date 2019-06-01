在对文件进行读写之前需要与该文件建立一个通道，也就是打开一个文件。而打开文件的连接过程可以是一个流或者一个文件描述符。有些处理文件的函数需要流，而其它的可能会对文件描述符进行操作，在结束读写的时候需要关闭文件。文件描述符一般是 `int` 类型，而流则一般是 `FILE *` 对象。

文件描述符给 I/O 提供了一个原始的底层的接口。文件描述符和流都能表示对如 terminal 这样的设备的连接，也可以作为普通的文件或者被管道和 socket 用来与其它进程进行连接。但是如果要对特殊的设备执行特定的控制操作则只能使用文件描述符，因为没有流提供这种支持。如果需要进行特殊种类的输入或输出比如非阻塞I/O，那么也只能使用文件描述符。

流提供了基于原始文件描述符设备的高层接口，使用流的优点是对于流上面的输入输出操作存在更丰富且强大的工具。文件描述符接口只提供了操作字符块的简单函数，而流接口则提供了强大的格式化输入输出函数比如 `printf` 和 `scanf` ，也提供了对于字符和面向行的输入输出。既然流是基于文件描述符来实现的，故而可以将流解开并使用对于文件描述符的底层操作。相对应的也可以将一个连接打开为文件描述符然后让一个流与该文件描述符相关联。

在 GNU 系统和所有的 POSIX.1 系统中，文件的位置一般都是使用一个整数来表示距离文件开始的字节数。当文件刚打开的时候文件位置通常被设置为文件的开始，每次一个字符被读或者写时文件位置都会增加。也就是说对文件的访问只能时线性的， 允许在任意位置读写的文件被称为随机存取（random-access）文件。可以通过 `fseek` 函数来改变流上的文件位置或者 `lseek` 来改变文件描述符上的文件位置。对已打开的流或文件描述符进行添加操作会顺序的加到文件的结尾，而不会受文件位置的影响。但是文件位置在这时依然会控制文件读取的位置。几个程序可以同时对一个文件进行读取，而每个文件打开操作都会新建一个新的文件位置，这样不同的程序就能按照自己的节奏来对文件进行读取。但是如果在打开一个描述符之后通过复制得到另一个描述符，这时候这两个描述符会共享同样的文件位置。

## Input/Output on Streams

因为历史原因C语言中代表流的数据结构被称作 `FILE` 而不是 stream， 对于流的操作大多数的库函数都是处理 `FILE *` ，而这又有可能和文件指针混淆。标准的输入输出流包括 `FILE * stdin` , `stdout` 和 `stderr` ，如果想要将标准输出重定向到一个文件的话可以使用

```c++
fclose (stdout);
stdout = fopen ("standard-output-file", "w");
```

使用 `fopen` 函数可以将一个文件打开为一个 `FILE *` 流，相应的使用 `fclose` 可以关闭对应的流。

### Streams and Threads

POSIX标准要求默认情况下流操作是原子操作。 即，同时在两个线程中为同一个流发出两个流操作将导致操作被执行，就好像它们是顺序发出的一样。在读取或写入时执行的缓冲操作受到保护，不受同一流的其他使用的影响。 为此，每个流都有一个内部锁定对象，必须（隐式）获取才能完成任何工作。但是在某些情况下，这还不够，而且还有一些情况需要这样做。 如果程序需要多个流函数调用以原子方式发生，则隐式锁定是不够的。 一个例子是如果程序想要生成的输出行是由几个函数调用创建的。 这些函数本身只能确保它们自己的操作的原子性，而不是所有函数调用的原子性。 为此，必须在应用程序代码中执行流锁定。如下的代码可以在多线程应用中自动产生一个输出行

```c
FILE *fp;
{
    ...
    flockfile (fp);
    fputs ("This is test number ", fp);
    fprintf (fp, "%d\n", test);
    funlockfile (fp)
}
```

如果没有进行显式的锁定 `fp` 可能会出现当 fputs 调用返回而 fprintf还未被调用的时候，另外一个线程使用了fp， 然后会导致输出的结果没有接在字符串 This is test number 的后面。

使用时lock和unlock的次数必须是相等的，而如果使用`ftrylockfile` 来进行锁定的话，则一定要根据其返回值判断是否成功锁定然后进行解锁。

```c
void
foo (FILE *fp)
{
    if (ftrylockfile (fp) == 0)
    {
        fputs ("in foo\n", fp);
    	funlockfile (fp);
    }
}
```

有两种方法可以避免使用锁定，一种是使用后缀 `_unlocked` 变体函数，这些变体和没有后缀的函数功能相同，只不过不会锁定流。这些函数会更快，因为锁定操作无论是否获取锁都会造成性能损失。一般来说 `putc` 和 `getc` 非常简单所以传统上是使用宏来实现，但是如果有锁的要求的话这些函数就不能使用宏来实现，但是在 `putc_unlocked` 中则仍然可以使用宏来实现同样的功能。

```c
void
foo (FILE *fp, char *buf)
{
    flockfile (fp);
    while (*buf != '/')
    putc_unlocked (*buf++, fp);
    funlockfile (fp);
}
```

如果在此示例中将使用putc函数并且缺少显式锁定，则putc函数必须在每次调用时获取锁定，可能多次取决于循环何时终止。 以上面说明的方式编写它允许使用putc_unlocked宏，这意味着没有锁定和直接操作流的缓冲区。

另一种避免锁的方式是使用Solaris引入的非标准函数如 `__fsetlocking` 。

### Stream Buffering

写入流的字符通常会积累起来然后以一整块异步发送给文件，而不是立即由应用程序发送出去。类似的流通常从主机环境取得输入块而不是一个字符一个字符的获得，这就是缓冲。一般使用流进行交互式操作时可能会出现字符并没有立即出现的现象。新打开的流通常都是完全缓存的，唯一的例外就是一个连接到像终端这样的交互式设备的流通常都是行缓存。

一般存在三种缓冲策略：

* 写入或读取无缓冲流的字符将尽快单独传输到文件或从文件传输。
* 当遇到换行符时，写入行缓冲流的字符以块的形式发送到文件。
* 写入完全缓冲流或从完全缓冲流读取的字符以任意大小的块传输到文件或从文件传输。

对交互设备使用行缓冲意味着以换行符结尾的输出消息将立即出现，没有以换行符结尾的消息可能出现也可能不会立即出现，如果希望立即出现的话应该使用 `fflush` 来显式的刷新缓冲输出。

在打开一个流并且还没有做其它操作时，可以使用 `setvbuf` 函数来显式的设置想要使用哪种缓冲方式，如使用完全缓冲可以设置 `_IOFBF` 。

### Other Kinds of Streams

GNU C 库还提供了定义不需要连接到一个打开的文件的流，比如可以对一个字符串进行输入或输出的流也就是字符串流，这种流被用来实现 `sprintf` 和 `sscanf` 函数，另外还可以创建自定义的对任何对象进行操作的流。

对于字符串流，函数 `fmemopen` 和 `open_memstream` 能够对字符串或者内存缓冲区进行I/O操作。

```c
#include <stdio.h>
#include <string.h>

static char buffer[] = "foobar";
int
main (void)
{
    int ch;
    FILE *stream;
    stream = fmemopen (buffer, strlen (buffer), "r");
    while ((ch = fgetc (stream)) != EOF)
    printf ("Got %c\n", ch);
    fclose (stream);
    return 0;
}

```

```c
#include <stdio.h>
int
main (void)
{
    char *bp;
    size_t size;
    FILE *stream;
    stream = open_memstream (&bp, &size);
    fprintf (stream, "hello");
    fflush (stream);
    printf ("buf = `%s', size = %zu\n", bp, size);
    fprintf (stream, ", world");
    fclose (stream);
    printf ("buf = `%s', size = %zu\n", bp, size);
    return 0;
}
```

自定义流 `custom streams` 允许能够对任意的数据来源进行读写，在每一个自定义流中都有一个特殊的称作 `cookie` 的对象，用来记录获取或者存储读写的位置。函数库中提供的流不会直接访问 cookie的内容，而是使用 `void *` 来记录他们的地址。要实现自定义流需要确定如何在特定的位置获取或者存储数据，这通过定义钩子函数 read、write、改变文件位置和关闭流的函数。

##  Low-Level Input/Output

一般来说使用I/O流通常更灵活且方便，因此只有在必要的时候才会选用描述符级别的函数，这些使用描述符的场景包括：

* 用于读取大块的二进制文件
* 在解析之前将整个文件读入核心
* 执行除数据传输之外的操作，而这些操作只能使用描述符来完成。（可以通过 `fileno ` 函数来获得对应流的描述符）
* 为了将描述符传递给子进程。（子进程可以通过描述符来创建自己的流，但是不能直接继承流）

使用 `open` 函数打开文件会返回一个文件描述符， `creat` 函数可以用来创建文件，其本质上会调用 `open` 函数。针对文件描述符的原始I/O操作包括 read、write以及lseek等。使用 `fileno` 函数可以获得流的文件描述符，相应的使用 `fdopen` 可以通过文件描述符来创建一个流。

###  Dangers of Mixing Streams and Descriptors

可以有很多文件描述符和流连接到同一个文件，简称为通道。其中需要注意的是要避免混淆通道，尤其是共享同一个文件位置的链接通道和拥有自己的文件位置的独立通道。

链接通道（Linked Channels）共享同样的文件位置，产生链接通道的方式有多种。使用 `fdopen` 从文件描述符获取流、使用 `fileno` 从流获取文件描述符都会产生连接通道。另外使用 `dup` 和 `dup2` 复制文件描述符时还有使用 `fork` 创建子进程时继承到的描述符也是连接通道。对于不支持随机访问的文件，比如终端和管道，所有的通道都是链接的。对于支持随机访问的文件，所有的附加型输出流都是相互链接的。如果已经使用一个流用来I/O，然后又要使用另一个连接到该流的通道，可以是流或者文件描述符都需要在使用之前清理前面使用的流，也就是 `Cleaing Streams` 。终止一个进程或者在进程中执行一个新的程序都会销毁进程中所有的流，如果连接到这些流的描述符存在于其它进程中，它们的文件位置会变得未定义，为了避免这种情况，在销毁流之前一定要进行清理。

独立通道（Independent Channels）存在于为一个可查找的文件单独打开通道时，每个通道都有自己的文件位置。系统独立的处理每个通道，在大部分情况下这种情况时可预测并且自然的，每个通道可以 顺序的读取自己的文件位置。然而如果有些通道是流的话则需要注意：

* 在使用输出流并且在做其它可能会从文件中同样位置读写的操作时应该清理该输出流
* 在从输入流读取数据之前并且该数据有可能被其它的独立通道修改时应该清理该输入流。否则可能读取到流缓冲中过时的数据

如果对一个通道文件末尾输出一定会必定会造成其它的独立通道位置在新的结尾之前的某个位置。不可能可靠的在写之前将文件位置设置为新的 文件结尾，因为文件在被设置文件位置时始终有可能被其它的进程所扩展。取而代之的是使用附加型描述符或流，因为它们总是在当前文件的结尾进行输出。为了让文件结尾位置精确，在使用流时一定要清理输出通道。

对于不支持随机访问的文件，两个通道不可能有单独的文件指针，读写这种文件的通道总是链接的，从来没有独立。附加型通道也总是链接的。

清理流可以使用 `fflush` ，如果知道流已经是干净的可以跳过。当缓冲是空的时候流是干净的，例如没有缓冲的流永远都是干净的。在文件末尾的输入流是干净的，当行缓冲流的最后一个输出字符是换行的时候是干净的。然而，一个刚打开的流可能不是干净的因为其输入缓冲可能不空。当流对非随机访问文件输入时是不可能清理流的。这些流通常是预先读取的，并且当文件不是随机访问时，没有办法回馈已经读取的多余数据。当输入流从随机访问文件读取时， `fflush` 清理了流，但是却让文件指针处于不可预测的位置，在做进一步的I/O之前要设置文件指针。关闭一个仅输出流也会执行 `fflush` ，因此关闭仅输出流时一个有效的清理输出流的方法。在使用描述符进行控制操作（如设置终端模式）之前，无需清理流; 这些操作不会影响文件位置，也不会受其影响。但是，文本已经“输出”到流但仍然由流缓冲，在随后刷新时将受到新的终端模式的限制。 要确保当时生效的终端设置涵盖“过去”输出，请在设置模式之前刷新该终端的输出流。

### Other Kinds of I/O

有些应用可能需要读写内存中分布的多个缓冲区，尽管可以通过多次调用 `read` 或 `write` 来实现，但这并不高效因为每个内核调用都会产生开销。取而代之很多平台使用一个系统调用来提供特殊的高速原语来实现分散-集中（scatter-gather）操作，GNU C库提供了这些接口统一的模拟。这些函数都使用 `iovec` 结构来控制，它描述了缓冲的位置和大小。使用如 `readv` 函数可以从文件描述符中读取内容并将结果依次保存到 `const struct iovec*` 数组中，当缓冲填满了则保存到下一个缓冲。

对于在同一个文件系统上的两个文件之间复制数据可以使用 `copy_file_range` 接口，但是该函数指挥复制文件数据，不会复制像权限或扩展属性等元数据。

现代操作系统都允许使用 `mmap` 来将文件映射到内存，这样就能像访问数组一样在内存中直接访问文件，这样会比读写操作更加高效。

#### Waiting for Input or Output

有时候一个程序需要接受从多个通道来的输入，比如一个程序通过管道或者sockets来充当几个进程的服务器时。在这种时候不能使用 `read` ，因为这会阻塞程序直到在特定的文件描述符上有输入，而其它通道的输入却不会唤醒程序。可以设置为非阻塞模式并且轮转每个文件描述符，但是这非常低效。更好的解决方案是使用 `select` 函数，这会阻塞程序直到文件描述符集合上的任意一个输入或输出准备好了，文件描述符集合也就是 `fd_set` 对象。

#### Sync and Locks

现代OS中普通的 I/O操作可能并不是同步执行，有时候需要使用 `sync` 和 `fsync` 等函数来进行读写的同步操作。

POSIX标准定义了一套新的I/O操作可以显著减少应用花在等待I/O上的时间，新的函数让程序能够初始化多个I/O操作并且马上恢复正常的工作同时I/O操作并行执行，也就是异步I/O。异步I/O操作由数据结构 `struct aiocb` 来控制，存在 `aio_read` 等接口来进行I/O。

使用 `fcntl` 函数可以对文件描述符执行各种其它操作，包括查询或设置描述文件描述符状态的标志，操作记录锁等。之前提到使用 `dup` 和 `dup2` 可以复制文件描述符。文件描述符可以设很多标志，包括文件访问模式是否允许写入以及打开时是创建文件还是无阻塞的打开等。

打开文件描述符锁在与进程相关的锁相同的情况下很有用。 它们还可以用于通过让每个线程执行其自己的文件打开来同步同一进程中的线程之间的文件访问，以获得其自己的打开文件描述符。因为仅在关闭引用打开文件描述的最后一个文件描述符时自动释放打开文件描述锁，所以此锁定机制避免了由于库例程在应用程序不知道的情况下打开和关闭文件而无意中释放锁的可能性。 与进程相关的锁一样，打开文件描述锁是建议性的。

```c
#define _GNU_SOURCE
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <pthread.h>
#define FILENAME "/tmp/foo"
#define NUM_THREADS 3
#define ITERATIONS 5
void *
thread_start(void *arg)
{
    int i, fd, len;
    long tid = (long)arg;
    char buf[256];
    struct flock lck = {
        .l_whence = SEEK_SET,
        .l_start = 0,
        .l_len = 1,
    };
    fd = open("/tmp/foo", O_RDWR | O_CREAT, 0666);
    for (i = 0; i < ITERATIONS; i++)
    {
        lck.l_type = F_WRLCK;
        fcntl(fd, F_OFD_SETLKW, &lck);
        len = sprintf(buf, "%d: tid=%ld fd=%d\n", i, tid, fd);
        lseek(fd, 0, SEEK_END);
        write(fd, buf, len);
        fsync(fd);
        lck.l_type = F_UNLCK;
        fcntl(fd, F_OFD_SETLK, &lck);
        /* sleep to ensure lock is yielded to another thread */
        usleep(1);
    }
    pthread_exit(NULL);
}
int main(int argc, char **argv)
{
    long i;
    pthread_t threads[NUM_THREADS];
    truncate(FILENAME, 0);
    for (i = 0; i < NUM_THREADS; i++)
        pthread_create(&threads[i], NULL, thread_start, (void *)i);
    pthread_exit(NULL);
    return 0;
}
```

此示例创建三个线程，每个线程循环五次，附加到文件。 通过打开的文件描述锁序序化访问该文件。

#### Generic I/O Control operations

GNU 系统能够处理在很多不同设备上大部分的输入输出操作，然而很多设备也会有少量特有的操作不能使用 `read` 和 `lseek` 等接口处理，比如：

* 改变终端使用的字符字体
* 告诉磁带系统倒带或快进。 （因为它们不能以字节为增量移动，所以lseek不适用）。
* 从驱动弹出硬盘
* 从CD-ROM驱动播放音轨
* 维护网络路由表

尽管 sockets 和终端这样的设备都会有特殊的函数来处理，为所有的这些情况都去创建函数是不现实的，因此可以使用 `ioctl` 函数来处理这些特殊情况。

## File System Interface

文件系统接口提供了对文件或目录的操作接口而不是对文件内容的处理，一般使用函数 `getcwd` 可以获取当前的工作目录， `chdir` 可以改变工作目录。对于文件目录的访问可以使用 `readdir` 函数访问目录流来获取入口，这些入口表示为 `struct dirent` 对象，每个入口的文件名保存在 `d_name` 成员中。

一般使用 `DIR` 数据类型来表示一个目录流，可以通过 `opendir` 函数获取一个目录流指针 `DIR *` ，而不应该自己分配 `struct dirent` 或 `DIR` ，也可以使用 函数 `fdopendir` 从文件描述符来打开。对于文件流的访问使用 `readdir` 函数，其每次都获取文件流中的下一个入口。

```c
#include <stdio.h>
#include <sys/types.h>
#include <dirent.h>
int main(void)
{
    DIR *dp;
    struct dirent *ep;
    dp = opendir("./");
    if (dp != NULL)
    {
        while (ep = readdir(dp))
            puts(ep->d_name);
        (void)closedir(dp);
    }
    else
        perror("Couldn't open the directory");
    return 0;
}
```

对于文件流可以进行随机访问，使用 `rewinddir` 函数可以重新初始化已打开且访问过的目录流，而 `telldir` 函数则可以获取当前文件流的文件位置，使用 `seekdir` 可以设置文件流的文件位置。

使用 `scandir` 可以选择目录中条目的子集，可以将其排序。

```c
#include <stdio.h>
#include <dirent.h>
static int
one(const struct dirent *unused)
{
    return 1;
}
int main(void)
{
    struct dirent **eps;
    int n;
    n = scandir("./", &eps, one, alphasort);
    if (n >= 0)
    {
        int cnt;
        for (cnt = 0; cnt < n; ++cnt)
            puts(eps[cnt]->d_name);
    }
    else
        perror("Couldn't open the directory");
    return 0;
}
```

对于目录树结构可以使用 `ftw` 函数来进行遍历，通过传入回调函数来进行处理。POSIX系统中目录树并不是严格意义上的树结构，因为存在多个文件名指向同一个文件，也就是链接，可以使用 `link` 函数来创建硬链接，使用 `symlink` 来创建软链接。文件的删除可以使用 `unlink` 或 `remove` ，文件夹的删除使用 `rmdir` ，重命名可以使用 `rename` 函数，文件夹的创建使用 `mkdir` 。文件包含的很多属性都可以通过 `stat` 来获取，`fstat` 可以从文件描述符获取属性。同时还可以使用函数来测试文件是否属于某种类型的文件，如 `S_ISSOCK` 测试文件是否为socket。另外还可以使用 `chown` 或 `fchown` 来改变文件的所有权，文件的权限可以通过 `umask` 函数来修改， `getumask` 可以获得相应标志，`chmod` 或 `fchmod` 可以设置文件的访问模式。`accesss` 可以测试文件是否能够被访问或以何种方式被访问。使用 `utime` 可以修改文件的时间，`truncate` 或 `ftruncate` 函数可以修改文件的大小。

使用 `mknod` 可以创建特殊的文件，`tmpfile` 函数可以创建临时的二进制文件。

## Pipes and FIFOs

管道是用来进行进程间通信（IPC）的一种机制，从一个进程写入管道的数据会被另一个进程读取，数据处理的顺序是FIFO。管道没有名字，是为一次使用而创建，并且两端必须从创建管道的进程继承。一个FIFO的特殊文件和管道类似，但是，FIFO不是匿名的临时连接，而是具有与任何其他文件类似的名称。进程通过名字打开FIFO并且按顺序通过它来通信。

管道或者FIFO都必须在两端同时保持开放，如果从一个管道或者FIFO文件读取数据但是并没有任何进程写入，读取会返回EOF。而写入一个管道或者FIFO却没有进程读数据会被视作错误，产生一个 `SIGPIPE` 信号，如果这个信号被处理或者阻塞会返回 `EPIPE` 错误。管道和FIFO都不允许文件位置，其读写操作都是顺序，从文件的开始位置读取，从文件的结尾写入。

创建管道的原语是 `pipe` 函数，这会同时创建管道的读和写两端。单个线程使用管道没有意义，只有在一个进程创建子进程的时候管道才变得实用，可以是父子进程通信，也可以是两个子进程通信。

```c
#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
/* Read characters from the pipe and echo them to stdout. */
void read_from_pipe(int file)
{
    FILE *stream;
    int c;
    stream = fdopen(file, "r");
    while ((c = fgetc(stream)) != EOF)
        putchar(c);
    fclose(stream);
}
/* Write some random text to the pipe. */
void write_to_pipe(int file)
{
    FILE *stream;
    stream = fdopen(file, "w");
    fprintf(stream, "hello, world!\n");
    fprintf(stream, "goodbye, world!\n");
    fclose(stream);
}
int main(void)
{
    pid_t pid;
    int mypipe[2];
    /* Create the pipe. */
    if (pipe(mypipe))
    {
        fprintf(stderr, "Pipe failed.\n");
        return EXIT_FAILURE;
    }
    /* Create the child process. */
    pid = fork();
    if (pid == (pid_t)0)
    {
        /* This is the child process.
           Close other end first. */
        close(mypipe[1]);
        read_from_pipe(mypipe[0]);
        return EXIT_SUCCESS;
    }
    else if (pid < (pid_t)0)
    {
        /* The fork failed. */
        fprintf(stderr, "Fork failed.\n");
        return EXIT_FAILURE;
    }
    else
    {
        /* This is the parent process.
           Close other end first. */
        close(mypipe[0]);
        write_to_pipe(mypipe[1]);
        return EXIT_SUCCESS;
    }
}
```

管道通常用来从运行为子进程其它程序发送或接收数据，一般都会使用 `pipe` 、`fork` 、`dup2`以及 `exec` 的结合。或者也可以使用 `popen` 和 `pclose` 函数，优点是更加简便，但是不太灵活。 `popen` 函数会将command命令执行为一个子进程。

```c
#include <stdio.h>
#include <stdlib.h>

void write_data(FILE *stream)
{
    int i;
    for (i = 0; i < 100; i++)
        fprintf(stream, "%d\n", i);
    if (ferror(stream))
    {
        fprintf(stderr, "Output to stream failed.\n");
        exit(EXIT_FAILURE);
    }
}
int main(void)
{
    FILE *output;
    output = popen("more", "w");
    if (!output)
    {
        fprintf(stderr,
                "incorrect parameters or too many files.\n");
        return EXIT_FAILURE;
    }
    write_data(output);
    if (pclose(output) != 0)
    {
        fprintf(stderr,
                "Could not run more or other error.\n");
    }
    return EXIT_SUCCESS;
}
```

创建FIFO特殊文件的方式是使用 `mkfifo` 函数，它可以根据给的我呢见名来创建一个FIFO的文件，只有在两端都被打开时才能进行输入输出操作。

对于管道而言，只要写入的数据不超过 `PIPE_BUF` 大小，那么对管道的操作就是原子的。当缓冲被填满之后，更多的写入会被阻塞直到有些字符被读取。

## Sockets

一个socket时一个泛化的进程间通信通道，和管道类似的是socket也表示为一个文件描述符。但是不同于管道socket支持没有关系的进程间通信，甚至是通过网络沟通允许在不同机器上的进程。常用的软件如 `telnet` 、 `rlogin` 、`rlogin` 、`ftp` 、`talk`等都使用socket。

GNU C库包含多种不同的sockets，其中 `SOCK_STREAM` 风格就像管道，而 `SOCK_DGRAM` 则被用来发送不可信的数据包。使用socket进行通信时开始要设置socket，一般通过 `socket` 函数来获取一个socket，然后用 `bind` 函数来绑定到特定的地址。使用 `getsockname` 函数可以读取socket的地址信息。

在本地使用socket进行进程间通信时设置的时本地命名空间，也就是PF_LOCAL 或 PF_UNIX 或 AF_LOCAL等，存在不同名字是为了兼容不同的系统。

```c
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
int make_named_socket(const char *filename)
{
    struct sockaddr_un name;
    int sock;
    size_t size;
    /* Create the socket. */
    sock = socket(PF_LOCAL, SOCK_DGRAM, 0);
    if (sock < 0)
    {
        perror("socket");
        exit(EXIT_FAILURE);
    }
    /* Bind a name to the socket. */
    name.sun_family = AF_LOCAL;
    strncpy(name.sun_path, filename, sizeof(name.sun_path));
    name.sun_path[sizeof(name.sun_path) - 1] = '\0';
    /* The size of the address is
       the offset of the start of the filename,
       plus its length (not including the terminating null byte).
       Alternatively you can just do:
       size = SUN LEN (&name);
    */
    size = (offsetof(struct sockaddr_un, sun_path) + strlen(name.sun_path));
    if (bind(sock, (struct sockaddr *)&name, size) < 0)
    {
        perror("bind");
        exit(EXIT_FAILURE);
    }
    return sock;
}
```

网络socket通信时使用 PF_INET 和 PF_INET6分别代表IPv4和IPv6。值得注意的是网络socket使用的地址结构是 `struct sockaddr_in` ，而本地socket使用的是 `struct sockaddr_un` 。

跟踪“众所周知”服务的数据库通常是文件 `/etc/services` 或来自命名服务器的等效文件。可以使用 `netdb.h` 中的工具如 `getservbyname` 或 `getservbyport` 等函数来获取对应的service，这些接口都会返回 `struct servent *` 类型，其中保存了service的一些信息。

针对互联网或不同系统大小端的问题，使用 `htons` 和 `ntohs` 等函数可以进行相应的转换。

互联网协议通常由名字而不是数字来确定，主机知道的协议存储在一个数据库中，可以是来自文件 `/etc/protocols` ，也可以是雷子命名服务器的等效文件。可以通过 `getprotobyname` 或者 `getprotobynumber` 等函数来获取协议类型 `struct protoent*`  ，其中保存了协议的信息。

关闭一个socket时使用的是 `shutdown` 函数,  `socketpair`函数能够维持一对已连接的sockets，它在使用时非常类似管道，主要的区别在于成对的socket能够进行双向通信。

对于数据的获取，首先需要进行socket的连接，发送数据的一端也就是一般说的客户端会使用 `connect` 尝试连接另一个socket，而服务端的进程则会使用 `listen` 开始允许socket接受连接，之后使用 `accept` 来接受连接。连接后可以使用 `getpeername` 来获取连接到的socket的信息，发送和接收数据可以使用 `send` 和 `recv` ，也可以直接对文件描述符进行读写。对于数据包风格的socket进行数据的传输使用 `sendto` 和 `recvfrom` 函数。

在互联网端口上提供服务的另一种方法是使用后台程序 `inetd` 来鉴定，这是一个一直在执行的程序，并且使用 select 一直在等待一个端口集合获取消息。当收到消息的时候，获取连接然后创建子进程并且执行对应的服务程序，可以在 `/etc/inetd.conf` 文件中进行配置。

使用 `getsockopt` 和 `setsockopt` 可以对socket设置各种选项。网络数据库记录了系统开发者知道的一系列网络，通常保存在 `/etc/networks` 文件中或者来自命名服务器的等效文件。网络数据库通常被像 `route` 这样的路由程序用到，但是对只是通过网络通信的程序则没有用到。使用 `getnetbyname` 和 `getnetbyaddr` 函数可以获得网络信息，保存在类型 `struct netent *` 中。

## Low-Level Terminal Interface

底层的终端接口提供函数可以用来关闭输入，可以设置串行行特性，如行速度和流量控制，也可以改变文件结尾标志字符、命令行编辑、发送信号以及类似的控制函数。

文件描述符可以关联到终端，使用 `isatty` 可以判断是否关联，如果关联到终端使用 `ttyname` 可以获得关联的文件名。

终端的输入队列指的也是预取缓存，保存着从终端获取的字符但是还没有被进程读取。而输出队列则相应的保存着还未被进程读取的数据。

底层的终端接口提供了对终端模式的设置，包括输入模式、控制模式以及本地模式，关于行速度（Line Speed）， 如果终端连接到一个序列行，终端的行速度可以进行设置。

### 参考文献
* [GNU C标准库 IO](https://www.gnu.org/software/libc/manual/)