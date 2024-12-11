import os
from kubernetes import client, config
from datetime import datetime, timezone
import time
import logging

#-Logging configuration----------------------------
logger = logging.getLogger('Culler_Logger')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Global Configuration
cull_threshold_seconds = int(os.getenv("CULL_THRESHOLD_SECONDS", "3600"))
pod_prefix = os.getenv("POD_PREFIX", "jupyter-x-")
namespace = os.getenv("POD_NAMESPACE", "default")
CHECK_INTERVAL = 30

def list_and_cull_pods():
    # Load incluster config
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(namespace)

    now = datetime.now(timezone.utc)
    for pod in pods.items:
        print(pod.metadata.name)
        # Filter JupyterHub-created pods, in my case in the format jupyter-x-21321521
        if not pod.metadata.name.startswith(pod_prefix):
            logger.info(f"No pods to cull found. Checking again in {CHECK_INTERVAL}s")
            continue

        # Calculate pod age
        start_time = pod.status.start_time
        if not start_time:
            logger.info(f"Pod {pod.metadata.name} has no start time.")
            continue
        age_seconds = (now - start_time).total_seconds()
        logger.info(f"Pod {pod.metadata.name} Age: {age_seconds}s, Threshold: {cull_threshold_seconds}s")

        # Cull pods older than threshold
        if age_seconds > cull_threshold_seconds:
            logger.info(f"Culling pod: {pod.metadata.name}, Age: {age_seconds}s")
            try:
                resp = v1.delete_namespaced_pod(pod.metadata.name, namespace)
                logger.info(f"Pod {pod.metadata.name} deleted successfully. Response: {resp}")
            except client.exceptions.ApiException as e:
                logger.info(f"Failed to delete pod {pod.metadata.name}: {e}")

# Runner config
if __name__ == "__main__":
    logger.info("Running custom culler for Jupyter hub.")
    while True:
        list_and_cull_pods()
        time.sleep(CHECK_INTERVAL)