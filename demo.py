import modal, os, sys

stub = modal.Stub("One-2-3-45")
volume = modal.NetworkFileSystem.new().persisted("One-2-3-45")

@stub.function(
    image=modal.Image.from_registry("chaoxu98/one2345:1.0")
    .pip_install("fire")
    .run_commands(
        "wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && \
        dpkg -i cloudflared-linux-amd64.deb"
    ),
    network_file_systems={"/content": volume},
    gpu="A10G",
    timeout=60000,
)
async def run():
    import atexit, requests, subprocess, time, re
    from random import randint
    from threading import Timer
    from queue import Queue
    def cloudflared(port, metrics_port, output_queue):
        atexit.register(lambda p: p.terminate(), subprocess.Popen(['cloudflared', 'tunnel', '--url', f'http://127.0.0.1:{port}', '--metrics', f'127.0.0.1:{metrics_port}'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
        attempts, tunnel_url = 0, None
        while attempts < 10 and not tunnel_url:
            attempts += 1
            time.sleep(3)
            try:
                tunnel_url = re.search("(?P<url>https?:\/\/[^\s]+.trycloudflare.com)", requests.get(f'http://127.0.0.1:{metrics_port}/metrics').text).group("url")
            except:
                pass
        if not tunnel_url:
            raise Exception("Can't connect to Cloudflare Edge")
        output_queue.put(tunnel_url)
    output_queue, metrics_port = Queue(), randint(8100, 9000)
    thread = Timer(2, cloudflared, args=(7860, metrics_port, output_queue))
    thread.start()
    thread.join()
    tunnel_url = output_queue.get()
    os.environ['webui_url'] = tunnel_url
    print(tunnel_url)

    os.environ['HF_HOME'] = '/content/cache/huggingface'
    os.system(f"git clone -b dev https://github.com/camenduru/One-2-3-45 /content/One-2-3-45")
    os.chdir(f"/content/One-2-3-45")
    os.system(f"git pull")
    # os.system(f"python download_ckpt.py")
    sys.path.append('/content/One-2-3-45')
    sys.path.append('/content/One-2-3-45/demo')
    os.chdir(f"/content/One-2-3-45/demo")
    os.system(f"python app.py")

@stub.local_entrypoint()
def main():
    run.remote()
