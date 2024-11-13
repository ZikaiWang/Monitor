from flask import Flask, jsonify, render_template
import psutil
import time

app = Flask(__name__)

# Initialize previous values for rate calculation
last_net_io = psutil.net_io_counters()
last_time = time.time()


@app.route('/')
def index():
    return render_template('index.html')


# Manual repair
def cache_with_expiration(seconds):
    def decorator(func):
        cache_data = {}  # 存储缓存数据和时间戳

        def wrapper(*args):
            current_time = time.time()
            # 检查缓存是否存在以及是否过期
            if args in cache_data:
                result, timestamp = cache_data[args]
                if current_time - timestamp < seconds:
                    return result
            # 调用函数并更新缓存
            result = func(*args)
            cache_data[args] = (result, current_time)
            return result

        wrapper.cache_clear = lambda: cache_data.clear()
        return wrapper

    return decorator


@app.route('/api/stats', methods=['GET'])
@cache_with_expiration(2.5)
def get_stats():
    global last_net_io, last_time

    # print("check")

    # Memory and CPU stats (no change)
    memory = psutil.virtual_memory()
    memory_data = {
        "used": memory.used / (1024 ** 3),  # GB
        "total": memory.total / (1024 ** 3),  # GB
        "percent": memory.percent
    }
    cpu = psutil.cpu_percent(interval=0)  # 即时获取CPU利用率

    # Disk stats (no change)
    disks = []
    for partition in psutil.disk_partitions():
        usage = psutil.disk_usage(partition.mountpoint)
        disks.append({
            "mountpoint": partition.mountpoint,
            "used": usage.used / (1024 ** 3),  # GB
            "total": usage.total / (1024 ** 3),  # GB
            "percent": usage.percent
        })

    # Network stats: Calculate rate in kB/s or MB/s
    net_io = psutil.net_io_counters()
    current_time = time.time()
    time_diff = current_time - last_time
    if time_diff > 0:  # Avoid division by zero
        sent_rate_kBps = (net_io.bytes_sent - last_net_io.bytes_sent) / 1024 / time_diff
        recv_rate_kBps = (net_io.bytes_recv - last_net_io.bytes_recv) / 1024 / time_diff
    else:
        sent_rate_kBps = recv_rate_kBps = 0.0

    # Update last values
    last_net_io = net_io
    last_time = current_time

    network = {
        "sent_rate_kBps": sent_rate_kBps,
        "recv_rate_kBps": recv_rate_kBps
    }

    return jsonify({
        "memory": memory_data,
        "cpu": cpu,
        "disks": disks,
        "network": network
    })


if __name__ == '__main__':
    app.run(debug=True)
