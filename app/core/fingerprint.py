import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.normalize import normalize_text

NON_APP_PACKAGES = {
    "site-packages",
    "dist-packages",
    "node_modules",
    "runtime",
    "java",
    "javax",
    "sun",
    "org.springframework",
    "org.apache",
    "python3",
    "lib/python",
}

# Regexes for stack trace formats
_PY_FRAME_RE = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+([a-zA-Z0-9_<>\.]+)')
_JAVA_FRAME_RE = re.compile(
    r"at\s+([a-zA-Z0-9_\$]+(?:\.[a-zA-Z0-9_\$]+)+)\.([a-zA-Z0-9_\$<>]+)\(([^:]+):(\d+)\)"
)
_NODE_FRAME_1_RE = re.compile(r"at\s+([a-zA-Z0-9_\$<>]+)\s+\(([^:]+):(\d+):(\d+)\)")
_NODE_FRAME_2_RE = re.compile(r"at\s+([^:]+):(\d+):(\d+)")
_GO_FUNC_RE = re.compile(r"^([a-zA-Z0-9_\/\.\-\%]+\.[a-zA-Z0-9_]+)\(.*\)")
_GO_FILE_RE = re.compile(r"^\s+([^\s:]+):(\d+)")

_EXC_TYPE_RE = re.compile(r"([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.*)")


@dataclass
class Frame:
    file: str
    function: str
    is_app: bool


def _is_app_frame(file_path: str, func_name: str) -> bool:
    normalized_path = file_path.replace("\\", "/").lower()
    for non_app in NON_APP_PACKAGES:
        if non_app in normalized_path:
            return False
    if file_path.startswith("<") and file_path.endswith(">"):
        return False
    return True


def _last_two_segments(path_str: str) -> str:
    p = Path(path_str)
    parts = p.parts
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1] if parts else path_str


def parse_stack_trace(text: str) -> list[Frame]:
    frames: list[Frame] = []
    lines = text.splitlines()

    # 1. Python format
    py_matches = _PY_FRAME_RE.findall(text)
    if py_matches:
        for file_path, line_no, func_name in py_matches:
            is_app = _is_app_frame(file_path, func_name)
            frames.append(
                Frame(file=_last_two_segments(file_path), function=func_name, is_app=is_app)
            )
        return frames

    # 2. Java format
    java_matches = _JAVA_FRAME_RE.findall(text)
    if java_matches:
        for class_pkg, method_name, file_name, line_no in java_matches:
            is_app = not any(
                class_pkg.startswith(p)
                for p in ("java.", "javax.", "sun.", "org.springframework.", "org.apache.")
            )
            frames.append(
                Frame(file=file_name, function=f"{class_pkg}.{method_name}", is_app=is_app)
            )
        return frames

    # 3. Node format
    for line in lines:
        m1 = _NODE_FRAME_1_RE.search(line)
        if m1:
            func_name, file_path, line_no, col = m1.groups()
            is_app = _is_app_frame(file_path, func_name)
            frames.append(
                Frame(file=_last_two_segments(file_path), function=func_name, is_app=is_app)
            )
            continue
        m2 = _NODE_FRAME_2_RE.search(line)
        if m2:
            file_path, line_no, col = m2.groups()
            is_app = _is_app_frame(file_path, "")
            frames.append(
                Frame(file=_last_two_segments(file_path), function="anonymous", is_app=is_app)
            )
    if frames:
        return frames

    # 4. Go format
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m_func = _GO_FUNC_RE.match(line)
        if m_func and i + 1 < len(lines):
            func_name = m_func.group(1)
            next_line = lines[i + 1]
            m_file = _GO_FILE_RE.match(next_line)
            if m_file:
                file_path = m_file.group(1)
                is_app = not file_path.startswith("runtime/") and "pkg/mod" not in file_path
                frames.append(
                    Frame(file=_last_two_segments(file_path), function=func_name, is_app=is_app)
                )
                i += 2
                continue
        i += 1

    return frames


def fingerprints(text: str) -> list[str]:
    """Computes stack fingerprint and message fingerprint for exact-match recall."""
    fps: list[str] = []
    if not text:
        return fps

    frames = parse_stack_trace(text)
    app_frames = [f for f in frames if f.is_app]

    # Extract exception type
    exc_type = "UnknownException"
    exc_match = _EXC_TYPE_RE.search(text)
    if exc_match:
        exc_type = exc_match.group(1)

    # 1. Stack fingerprint (if app frames exist)
    if app_frames:
        innermost = app_frames[-3:]  # innermost 3 application frames
        formatted_frames = [f"{f.file}:{f.function}" for f in innermost]
        raw_stack_fp = f"{exc_type}|" + "|".join(formatted_frames)
        stack_fp = hashlib.sha1(raw_stack_fp.encode("utf-8")).hexdigest()[:16]
        fps.append(stack_fp)

    # 2. Message fingerprint from first error line
    for line in text.splitlines():
        clean_line = line.strip()
        if clean_line:
            norm_line = normalize_text(clean_line)
            msg_fp = hashlib.sha1(norm_line.encode("utf-8")).hexdigest()[:16]
            fps.append(msg_fp)
            break

    return fps
