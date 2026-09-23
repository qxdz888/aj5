#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量 Git 推送助手（无 git.exe 环境）
=====================================
用 dulwich + paramiko 完成：clone/拉取 → 只复制「新增或变更」的文件 → commit → push。

关键点（踩过的坑，别改）：
1) 自定义 SSH Vendor：run_command 必须返回「单个对象」，同时具备
   .read/.write/.close/.can_read 和 .stderr 属性。
2) porcelain.commit(...) 只推进 HEAD；必须显式 r.refs[BRANCH] = r.head() 再 push，
   否则远端分支指针不动（看起来推成功、实际远端没变化）。
"""
import os, sys, shutil, hashlib
from pathlib import Path
from datetime import datetime

try:
    from dulwich import porcelain
    from dulwich.repo import Repo
    from dulwich.client import get_transport_and_path
    import paramiko
    HAVE_DEPS = True
except Exception as e:
    HAVE_DEPS = False
    _IMPORT_ERR = str(e)


# ─────────────────── paramiko over dulwich SSH vendor ───────────────────
def _build_vendor():
    from dulwich.client import SSHVendor, StrangeHostname

    class _ChanFile:
        def __init__(self, chan, write=False):
            self.chan = chan
            self.write = write
        def read(self, n=-1):
            return self.chan.recv(max(n, 1)) if n is not None and n > 0 else self.chan.recv(4096)
        def write(self, data):
            self.chan.sendall(data)
        def close(self):
            pass
        def can_read(self):
            return self.chan.recv_ready()

    class _Proc:
        def __init__(self, client, cmd):
            self.client = client
            self.chan = client.get_transport().open_session()
            self.chan.exec_command(cmd)
            self.stdout = _ChanFile(self.chan)
            self.stderr = _ChanFile(self.chan)
            self.stdin = _ChanFile(self.chan, write=True)

    class ParamikoVendor(SSHVendor):
        def run_command(self, host, command, username=None, port=None,
                        password=None, key_filename=None, allow_agent=True, **kw):
            if isinstance(command, (list, tuple)):
                command = " ".join(command)
            # 本环境 ~/.ssh/config 把 github.com 指到 ssh.github.com:443（绕过 22 口封锁）
            real_host, real_port = host, port or 22
            if host in ("github.com", "ssh.github.com"):
                real_host, real_port = "ssh.github.com", 443
            # 清掉 HTTP(S)_PROXY：paramiko 不走 HTTP 代理，但避免环境干扰
            saved = {}
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
                if k in os.environ:
                    saved[k] = os.environ.pop(k)
            try:
                # 修复：Git-Bash 子环境里 HOME 可能是 /c/Users/... 风格，paramiko 会据此把
                # known_hosts 解析成原生 Windows 打不开的路径，open 时抛 Permission denied，
                # 进而 host key 校验失败、握手被远端断开（表现为 get_refs "remote closed" /
                # send_pack "Host key verification failed"）。
                # 这里强制 HOME 指向 Windows 风格，并预加载本地 known_hosts，
                # 使 connect() 不再回退去读默认（可能损坏的）known_hosts。
                _win_home = os.environ.get("USERPROFILE") or r"C:\Users\Administrator.DESKTOP-K1RSGDC"
                os.environ["HOME"] = _win_home
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                _kh = os.path.join(_win_home, ".ssh", "known_hosts")
                try:
                    if os.path.exists(_kh):
                        client.load_system_host_keys(_kh)
                        client.load_host_keys(_kh)
                    else:
                        # 没有已知 hosts 时也放一条占位，让 _system_host_keys 非空，
                        # 阻止 connect() 回退重载默认文件
                        client._system_host_keys = paramiko.HostKeys()
                        client._system_host_keys["__placeholder__.invalid"] = {}
                except Exception:
                    client._system_host_keys = paramiko.HostKeys()
                    client._system_host_keys["__placeholder__.invalid"] = {}
                kw_extra = {}
                if key_filename:
                    kw_extra['key_filename'] = key_filename
                client.connect(real_host, port=real_port, username=username or 'git',
                               password=password, allow_agent=allow_agent,
                               look_for_keys=True, timeout=40, **kw_extra)
            finally:
                os.environ.update(saved)
            return _Proc(client, command)

    return ParamikoVendor()


def _install_vendor():
    from dulwich.client import SSHGitClient
    SSHGitClient.ssh_vendor = _build_vendor()


# ─────────────────── 核心：增量推送 ───────────────────
def incremental_push(base_dir, clone_dir, repo_url, branch="main",
                     subdirs=("images", "thumbs"), files=(), commit_msg=None):
    """
    只把「新增或变更」的文件复制进本地克隆并提交，已有的相同文件不动。
    返回 True/False。
    """
    if not HAVE_DEPS:
        print(f"[!!] 缺少依赖（dulwich/paramiko）：{_IMPORT_ERR}")
        return False

    base_dir = Path(base_dir)
    clone_dir = Path(clone_dir)

    # 统一走 SSH（本环境 HTTPS 会命中本地代理导致 502）
    if repo_url.startswith("https://github.com/"):
        repo_url = "git@github.com:" + repo_url[len("https://github.com/"):]
    print(f"[•] 远端: {repo_url}")

    # 清掉代理环境变量（避免 dulwich/paramiko 被干扰）
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)

    _install_vendor()

    # 1) 克隆或更新
    if not (clone_dir / ".git").exists():
        if clone_dir.exists():
            shutil.rmtree(clone_dir, ignore_errors=True)
        print(f"[•] 克隆 {repo_url} → {clone_dir}")
        porcelain.clone(repo_url, str(clone_dir), branch=branch.encode())
    else:
        print(f"[•] 拉取更新 {clone_dir}")
        try:
            porcelain.pull(str(clone_dir), repo_url,
                           refspecs=[f"refs/heads/{branch}:refs/heads/{branch}".encode()])
        except Exception as e:
            # dulwich 的 pull 在「已是最新」时返回元组也算异常路径，不能当失败
            msg = str(e)
            if "up to date" in msg.lower() or msg.startswith("(b'"):
                print("[•] 远端无新提交（已最新）")
            else:
                print(f"[!] pull 失败（继续用现有克隆）：{e}")

    repo = Repo(str(clone_dir))

    # 2) 收集本地文件 → 目标路径，逐个比对 md5，只复制「新增/变更」
    def md5(p):
        h = hashlib.md5()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()

    plan = []           # (src, dst_rel)
    for sub in subdirs:
        src_root = base_dir / sub
        if not src_root.exists():
            continue
        for r, _, fs in os.walk(src_root):
            for f in fs:
                sp = Path(r) / f
                rel = Path(sub) / sp.relative_to(src_root)
                plan.append((sp, rel))
    for f in files:
        sp = base_dir / f
        if sp.exists():
            plan.append((sp, Path(f)))

    added, updated, same = 0, 0, 0
    for sp, rel in plan:
        dp = clone_dir / rel
        if not dp.exists():
            dp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sp, dp)
            added += 1
        elif md5(sp) != md5(dp):
            shutil.copy2(sp, dp)
            updated += 1
        else:
            same += 1

    print(f"[•] 文件比对：新增 {added}，更新 {updated}，未变 {same}（共 {len(plan)}）")

    if added or updated:
        # 3) 提交
        porcelain.add(str(clone_dir), [b"."])
        st = porcelain.status(str(clone_dir))
        staged_n = len(st.staged.get('add', [])) + len(st.staged.get('modify', [])) + len(st.staged.get('delete', []))
        print(f"[•] 暂存 {staged_n} 项（新增/修改/删除）")

        if not commit_msg:
            commit_msg = f"sync: 增量更新 {added} 新增 / {updated} 修改 ({datetime.now():%Y-%m-%d %H:%M})"
        porcelain.commit(str(clone_dir),
                         message=commit_msg.encode('utf-8'),
                         author=b"aj5-bot <aj5-bot@local>",
                         committer=b"aj5-bot <aj5-bot@local>")

    # 4) 关键：显式把分支指针指到当前 HEAD，再 push
    head = repo.head()
    repo.refs[f"refs/heads/{branch}".encode()] = head
    print(f"[•] 本地 {branch} → {head.decode()[:10]}")

    # 4.5) 若本地 HEAD 已在远端，直接跳过（真正的「无需推送」判断）
    try:
        _c, _p = get_transport_and_path(repo_url)
        remote_refs = _c.get_refs(_p)
        rk = f"refs/heads/{branch}".encode()
        remote_head = remote_refs.get(rk) or remote_refs.get(b"HEAD")
        if remote_head and remote_head == head:
            print(f"[✓] 远端已是最新（{head.decode()[:10]}），无需推送")
            return True
        if remote_head:
            print(f"[•] 远端当前 {remote_head.decode()[:10]}，准备推送 {head.decode()[:10]}")
    except Exception as e:
        print(f"[!] 读取远端 ref 失败（仍尝试推送）：{e}")

    # dulwich 1.2.15：send_pack 不接受 refspecs 关键字，必须走 porcelain.push
    head_hex = head.decode()
    local_ref = f"refs/heads/{branch}"
    push_refspec = f"{local_ref}:{local_ref}"

    # porcelain.push 内部会用 repo.refs 的 HEAD 目标；显式传 refspecs 更稳
    result = porcelain.push(
        str(clone_dir),
        repo_url,
        refspecs=[push_refspec.encode()],
    )
    ref_status = getattr(result, "ref_status", None) or {}
    bad = {k: v for k, v in ref_status.items() if v is not None}
    if bad:
        print(f"[!!] 远端拒绝部分引用：{bad}")
        return False
    print(f"[✓] 推送完成 {local_ref} → {head_hex[:10]}（ref_status={ref_status or 'ok'}）")
    return True


if __name__ == '__main__':
    print("此模块由 sync.py 调用，一般不单独运行。")
