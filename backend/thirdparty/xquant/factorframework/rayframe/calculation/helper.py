import ray
import inspect
import os
import signal
import time
import subprocess


def get_docker_memory():
    with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as f:
        byte_memory_limit = int(f.read())
    with open('/sys/fs/cgroup/memory/memory.usage_in_bytes') as f:
        byte_memory_usage = int(f.read())
    return min(int((byte_memory_limit - byte_memory_usage) * 0.3), 5000000000)


def get_docker_cpu():
    with open('/sys/fs/cgroup/cpu/cpu.cfs_quota_us') as f:
        cpu_quota = int(f.read())
    with open('/sys/fs/cgroup/cpu/cpu.cfs_period_us') as f:
        cpu_period = int(f.read())
    return int(cpu_quota / cpu_period)



def _start_public_ray(num_cpus, ray_memory, env):
    stop_public_ray()
    # 启动分布式RAY集群主节点
    # ray start --head --num-cpus=4 --memory=10000000000
    result = subprocess.run(
        ["ray", "start", "--head", "--num-cpus={}".format(num_cpus), "--object-store-memory={}".format(ray_memory)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    if result.returncode == 0:
        # print(result.stdout)
        print("RAY集群主节点已启动成功")
        return True
    else:
        res_status = subprocess.run(
            ["ray", "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res_status.returncode == 0:
            print("RAY集群主节点已启动成功。")
            return True
        else:
            print(f"RAY集群主节点启动失败: {result.stderr}")
            return False


def start_public_ray(num_cpus=4, ray_memory=10, **options):
    # 启动分布式RAY集群主节点
    assert isinstance(ray_memory, int), "预设ray运行内存单位为G，数据类型为int"
    assert isinstance(num_cpus, int), "预设ray运行cpu数量，数据类型为int"
    ray_memory = ray_memory * 1000 * 1000 * 1000
    os.environ["NUMEXPR_MAX_THREADS"] = "36"
    env = os.environ.copy()
    i = 0
    while True:
        res = _start_public_ray(num_cpus, ray_memory, env)
        i += 1
        if res:
            break
        if i >= 5:
            print(f"RAY集群主节点连续{i}次启动失败。。。")
            break



def stop_public_ray():
    print("正在停止运行中的ray集群...")
    result = subprocess.run(
        ["ray", "stop"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode == 0:
        # 轮训检测RAY进程是否真的停止
        max_retries = 20  # 最大重试次数
        retry_count = 0
        
        while retry_count < max_retries:
            time.sleep(2)  # 每隔1秒检查一次
            
            # 使用ray status命令检测集群状态
            status_result = subprocess.run(
                ["ray", "status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if status_result.returncode != 0:
                # 如果ray status失败，说明RAY进程已经停止
                print("RAY集群已完全停止")
                break
            
            retry_count += 1
        
        else:
            # 如果循环结束还没有检测到停止，则输出警告
            print("Warning: RAY集群停止超时，请检查是否仍有残留进程！")
    
    else:
        print("Ray集群停止失败: ", result.stderr)
    time.sleep(5)

    
def set_ray_options11(num_cpus, object_store_memory, options, start_mode='task'):
    """
    start_mode: actor模式示num_cpus为1，task模式num_cpus为docker的所有cpu
    """
    if ray.is_initialized():
        raise Exception("Ray计算环境启动失败：当前有正在使用的Ray计算环境，请用ps -ef|grep ray查看并停止！")
    if num_cpus is None:
        num_cpus = max(1, get_docker_cpu() - 1)
    if options is None:
        options = {'local_mode': True}#
    if object_store_memory is None:
        object_store_memory = get_docker_memory()
    try:
        if not start_mode == 'actor':
            print('Ray启动占用的CPU数：{}'.format((num_cpus)))
            print('Ray启动占用的内存数：{}'.format(object_store_memory))
            ray.init(num_cpus=num_cpus, object_store_memory=object_store_memory, **options)
        else:
            print('Ray启动占用的CPU数：{}'.format(num_cpus))
            print('Ray启动占用的内存数：{}'.format(object_store_memory * 0.5))
            ray.init(num_cpus=num_cpus, object_store_memory=int(object_store_memory * 0.5), **options)
    except Exception as e:
        # print('Ray启动占用的CPU数：{}'.format((num_cpus)))
        # print('Ray启动占用的内存数：{}'.format(object_store_memory))
        raise e



def set_ray_options(num_cpus, object_store_memory, options, start_mode='task'):
    """
    start_mode: actor模式示num_cpus为1，task模式num_cpus为docker的所有cpu
    """
    if ray.is_initialized():
        ray.shutdown()
        raise Exception("Ray计算环境启动失败：当前有正在使用的Ray计算环境，请用ps -ef|grep ray查看进程，并用ray stop命令手动停止！")
    if num_cpus is None:
        num_cpus = max(1, get_docker_cpu())
    if options is None:
        options = {}
    if object_store_memory is None:
        object_store_memory = get_docker_memory()
    try:
        if not start_mode == 'actor':
            start_public_ray(num_cpus, int(object_store_memory/1000000000), **options)
            print('Ray启动占用的CPU数：{}'.format((num_cpus)))
            print('Ray启动占用的内存数：{}B'.format(object_store_memory))
            ray.init("auto")
        else:
            start_public_ray(1, int(object_store_memory * 0.5/1000000000), **options)
            print('Ray启动占用的CPU数：{}'.format(num_cpus))
            print('Ray启动占用的内存数：{}B'.format(object_store_memory * 0.5))
            ray.init("auto")
    except Exception as e:
        # print('Ray启动占用的CPU数：{}'.format((num_cpus)))
        # print('Ray启动占用的内存数：{}'.format(object_store_memory))
        raise e


def parse_callback_params(func, has_factor_list=False):
    sig = inspect.signature(func)
    parameters = sig.parameters
    new_params_dict = {}
    for pidx, param_key in enumerate(parameters):
        param = parameters[param_key]
        if param.name != 'self' and pidx == 0:
            print('ERROR: calc_callback第一个参数必须为self！当前为{}！'.format(param.name))
            os.killpg(os.getpgid(os.getpid()), signal.SIGINT)
        if not has_factor_list:
            if param.name != 'df_dict' and pidx == 1:
                print('ERROR: calc_callback第二个参数必须为df_dict！当前为{}！'.format(param.name))
                os.killpg(os.getpgid(os.getpid()), signal.SIGINT)
        else:
            if param.name != 'factor_list' and pidx == 1:
                print('ERROR: calc_callback第二个参数必须为factor_list！当前为{}！'.format(param.name))
                os.killpg(os.getpgid(os.getpid()), signal.SIGINT)
            if param.name != 'df_dict' and pidx == 2:
                print('ERROR: calc_callback第三个参数必须为df_dict！当前为{}！'.format(param.name))
                os.killpg(os.getpgid(os.getpid()), signal.SIGINT)
        try:
            if not param.default == param.empty:
                new_params_dict[param.name] = param.default
        except:
            # 无法识别的类型，必然是用户自定义传参
            new_params_dict[param.name] = param.default
    return new_params_dict
