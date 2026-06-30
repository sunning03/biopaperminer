"""mineru_client.py — MinerU 文档解析 API 客户端（优化版）

优化点：
- 使用 requests.Session 连接池
- 改进缓存逻辑，避免重复上传同一文件
- 减少不必要的文件读写
"""
import time
import zipfile
import requests
from pathlib import Path
from typing import Optional, Tuple
import logging
from urllib.parse import urljoin
import io
import hashlib

from biopaperminer.session_pool import get_session as _get_session

logger = logging.getLogger(__name__)


class MinerUClient:
    BASE_URL = "https://mineru.net"
    TASK_API = "/api/v4/extract/task"
    QUERY_API = "/api/v4/extract/task"
    BATCH_UPLOAD_API = "/api/v4/file-urls/batch"
    BATCH_QUERY_API = "/api/v4/extract-results/batch"

    def __init__(self, api_token: str, timeout: int = 120):
        self.api_token = api_token.strip()
        self.timeout = timeout
        self._session = _get_session(self.BASE_URL)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def submit_task(self, file_url: str, model_version: str = "vlm", language: str = "ch") -> Optional[str]:
        """提交解析任务，返回 task_id；失败返回 None。"""
        url = urljoin(self.BASE_URL, self.TASK_API)
        payload = {
            "url": file_url,
            "model_version": model_version,
            "language": language,
        }
        try:
            resp = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"MinerU submit error: {data.get('msg')}")
                return None
            return data.get("data", {}).get("task_id")
        except Exception as e:
            logger.error(f"MinerU submit exception: {e}")
            return None

    def query_task(self, task_id: str) -> Optional[dict]:
        """查询任务状态；返回 data 字段，失败返回 None。"""
        url = urljoin(self.BASE_URL, f"{self.QUERY_API}/{task_id}")
        try:
            resp = self._session.get(url, headers=self._headers(), timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"MinerU query error: {data.get('msg')}")
                return None
            return data.get("data")
        except Exception as e:
            logger.error(f"MinerU query exception: {e}")
            return None

    def wait_until_done(self, task_id: str, poll_interval: int = 3, max_wait: int = 600) -> Optional[str]:
        """轮询直到 done/failed；返回 full_zip_url（done）或 None（失败/超时）。"""
        start = time.time()
        while True:
            info = self.query_task(task_id)
            if not info:
                return None
            state = info.get("state")
            if state == "done":
                zip_url = info.get("full_zip_url")
                if not zip_url:
                    logger.error(f"MinerU done but no full_zip_url: task_id={task_id}")
                    return None
                return zip_url
            if state == "failed":
                logger.error(f"MinerU task failed: task_id={task_id}, err={info.get('err_msg')}")
                return None
            if time.time() - start > max_wait:
                logger.warning(f"MinerU task timeout: task_id={task_id}")
                return None
            time.sleep(poll_interval)

    def download_and_extract_zip(self, zip_url: str, target_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
        """下载 zip 并解压到 target_dir。返回 (full_md_path, layout_json_path)。"""
        try:
            resp = requests.get(zip_url, timeout=self.timeout)
            resp.raise_for_status()
            zip_bytes = io.BytesIO(resp.content)
            target_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_bytes) as zf:
                zf.extractall(target_dir)
            full_md = target_dir / "full.md"
            layout_json = target_dir / "layout.json"
            return (full_md if full_md.exists() else None,
                    layout_json if layout_json.exists() else None)
        except Exception as e:
            logger.error(f"download/extract zip failed: {e}")
            return (None, None)

    # ── 缓存：已解析文件的 SHA256 → md_text，避免重复调用 API ──
    _parse_cache: dict = {}

    def pdf_to_md(self, pdf_path: Path, output_dir: Optional[Path] = None) -> Optional[str]:
        """
        便捷方法：给定本地 PDF 文件，返回 MinerU 解析后的 Markdown 文本。
        优化：
        1. 先检查本地缓存的 full.md
        2. 再检查内存缓存（同进程内重复处理同一 PDF）
        3. 最后调用 API
        """
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_mineru"
        md_cache = output_dir / "full.md"

        # 策略1：本地缓存
        if md_cache.exists():
            try:
                return md_cache.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"读取本地缓存失败: {e}")

        # 策略2：内存缓存
        file_hash = self._file_hash(pdf_path)
        if file_hash in self._parse_cache:
            return self._parse_cache[file_hash]

        # 策略3：调用 API（批量上传模式）
        try:
            batch_id, data_id = self._batch_upload_file(pdf_path)
            if batch_id and data_id:
                zip_url = self._poll_batch_result(batch_id, data_id)
                if zip_url:
                    md_path, _ = self.download_and_extract_zip(zip_url, output_dir)
                    if md_path and md_path.exists():
                        md_text = md_path.read_text(encoding="utf-8")
                        # 写入内存缓存
                        self._parse_cache[file_hash] = md_text
                        return md_text
        except Exception as e:
            logger.error(f"MinerU API 调用失败: {e}")

        return None

    @staticmethod
    def _file_hash(path: Path) -> str:
        """计算文件 SHA256（用于去重）"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _batch_upload_file(self, pdf_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        使用 MinerU 批量上传接口上传一个本地文件。
        返回 (batch_id, data_id)；失败返回 (None, None)。
        """
        import os
        file_size = os.path.getsize(pdf_path)
        if file_size > 200 * 1024 * 1024:
            logger.error(f"文件 {pdf_path.name} 超过 200MB，无法通过 MinerU 解析")
            return (None, None)

        file_name = pdf_path.name
        data_id = self._file_hash(pdf_path)

        url = urljoin(self.BASE_URL, self.BATCH_UPLOAD_API)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }
        payload = {
            "files": [{"name": file_name, "data_id": data_id}],
            "model_version": "vlm",
        }
        try:
            # 1) 申请 batch_id 与上传 URL
            resp = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                logger.error(f"MinerU batch apply failed: {result.get('msg')}")
                return (None, None)

            batch_id = result.get("data", {}).get("batch_id")
            upload_urls = result.get("data", {}).get("file_urls", [])
            if not batch_id or not upload_urls:
                logger.error(f"MinerU batch apply missing batch_id or urls: {result}")
                return (None, None)

            upload_url = upload_urls[0]
            logger.info(f"MinerU batch apply success: batch_id={batch_id}")

            # 2) PUT 上传文件
            with open(pdf_path, "rb") as f:
                resp_upload = requests.put(upload_url, data=f, timeout=self.timeout * 2)
            if resp_upload.status_code != 200:
                logger.error(f"MinerU PUT upload failed: status={resp_upload.status_code}")
                return (None, None)

            logger.info(f"MinerU PUT upload success: {pdf_path.name}")
            return (batch_id, data_id)

        except Exception as e:
            logger.error(f"MinerU _batch_upload_file exception: {e}")
            return (None, None)

    def _poll_batch_result(
        self,
        batch_id: str,
        data_id: str,
        poll_interval: int = 3,
        max_wait: int = 600,
    ) -> Optional[str]:
        """轮询批量解析结果，返回 full_zip_url（done）或 None（失败/超时）。"""
        url = urljoin(self.BASE_URL, f"{self.BATCH_QUERY_API}/{batch_id}")
        start = time.time()
        while True:
            try:
                resp = self._session.get(url, headers=self._headers(), timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    logger.error(f"MinerU batch query error: {data.get('msg')}")
                    return None

                results = data.get("data", {}).get("extract_result", [])
                if not isinstance(results, list):
                    results = [results]

                for item in results:
                    if item.get("data_id") == data_id or item.get("file_name", "").startswith(data_id[:8]):
                        state = item.get("state")
                        if state == "done":
                            zip_url = item.get("full_zip_url")
                            if not zip_url:
                                logger.error(f"MinerU done but no full_zip_url: data_id={data_id}")
                                return None
                            return zip_url
                        if state == "failed":
                            logger.error(f"MinerU task failed: data_id={data_id}, err={item.get('err_msg')}")
                            return None
                        break

                if time.time() - start > max_wait:
                    logger.warning(f"MinerU batch poll timeout: batch_id={batch_id}, data_id={data_id}")
                    return None

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"MinerU _poll_batch_result exception: {e}")
                return None
