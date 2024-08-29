import sys
import os
import zlib
import hashlib
import time

def create_blob_entry(path: str, write=True):
    with open(path, "rb") as f:
        data = f.read()
    header = f"blob {len(data)}\0".encode("utf-8")
    store = header + data
    sha = hashlib.sha1(store).hexdigest()
    if write:
        dir_path = f".git/objects/{sha[:2]}"
        os.makedirs(dir_path, exist_ok=True)
        with open(f"{dir_path}/{sha[2:]}", "wb") as f:
            f.write(zlib.compress(store))
    return sha

def write_tree(path: str):
    if os.path.isfile(path):
        return create_blob_entry(path)
    
    contents = sorted(
        os.listdir(path),
        key=lambda x: x if os.path.isfile(os.path.join(path, x)) else f"{x}/",
    )
    
    tree_entries = []
    for item in contents:
        if item == ".git":
            continue
        full_path = os.path.join(path, item)
        mode = "100644" if os.path.isfile(full_path) else "40000"
        sha1 = write_tree(full_path)
        entry = f"{mode} {item}\0".encode() + int(sha1, 16).to_bytes(20, byteorder="big")
        tree_entries.append(entry)
    
    tree_content = b"".join(tree_entries)
    tree_header = f"tree {len(tree_content)}\0".encode()
    store = tree_header + tree_content
    sha1 = hashlib.sha1(store).hexdigest()
    
    dir_path = f".git/objects/{sha1[:2]}"
    os.makedirs(dir_path, exist_ok=True)
    with open(f"{dir_path}/{sha1[2:]}", "wb") as f:
        f.write(zlib.compress(store))
    
    return sha1

def main():
    if len(sys.argv) < 2:
        raise RuntimeError("No command provided")
    
    command = sys.argv[1]
    
    if command == "init":
        if not os.path.exists(".git"):
            os.makedirs(".git/objects")
            os.makedirs(".git/refs")
            with open(".git/HEAD", "w") as f:
                f.write("ref: refs/heads/main\n")
            print("Initialized empty Git repository")
        else:
            print("Git repository already initialized")
    
    elif command == "cat-file":
        if len(sys.argv) >= 4 and sys.argv[2] == "-p":
            blob_sha = sys.argv[3]
            try:
                with open(f".git/objects/{blob_sha[:2]}/{blob_sha[2:]}", "rb") as f:
                    raw = zlib.decompress(f.read())
                    _, content = raw.split(b"\0", maxsplit=1)
                    print(content.decode("utf-8"), end="")
            except FileNotFoundError:
                print(f"Object {blob_sha} not found.")
    
    elif command == "hash-object":
        if len(sys.argv) >= 4 and sys.argv[2] == "-w":
            file_name = sys.argv[3]
            if not os.path.exists(file_name):
                print(f"File {file_name} not found.")
                return
            with open(file_name, "rb") as f:
                file_content = f.read()
            header = f"blob {len(file_content)}\x00"
            store = header.encode("ascii") + file_content
            sha = hashlib.sha1(store).hexdigest()
            git_path = os.path.join(os.getcwd(), ".git/objects")
            dir_path = os.path.join(git_path, sha[0:2])
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, sha[2:]), "wb") as f:
                f.write(zlib.compress(store))
            print(sha, end="")
    
    elif command == "ls-tree":
        if len(sys.argv) >= 4 and sys.argv[2] == "--name-only":
            tree_sha = sys.argv[3]
            try:
                with open(f".git/objects/{tree_sha[:2]}/{tree_sha[2:]}", "rb") as f:
                    data = zlib.decompress(f.read())
                    _, binary_data = data.split(b"\x00", maxsplit=1)
                    while binary_data:
                        # Extract mode and name
                        mode_end = binary_data.find(b' ')
                        mode = binary_data[:mode_end].decode("utf-8")
                        name_end = binary_data.find(b'\x00', mode_end)
                        name = binary_data[mode_end + 1:name_end].decode("utf-8")

                        # Print the filename
                        print(name)

                        # Move to the next entry
                        binary_data = binary_data[name_end + 21:]  # Skip null byte and 20-byte SHA-1 hash
            except FileNotFoundError:
                print(f"Tree object {tree_sha} not found.")
    
    elif command == "write-tree":
        print(write_tree("./"))
    
    elif command == "commit-tree":
        if len(sys.argv) >= 7:
            tree_sha = sys.argv[2]
            parent_sha = sys.argv[4]
            commit_msg = sys.argv[6]
            timestamp = int(time.time())
            author = "yash-k <yashwanthkothakota@gmail.com>"
            commit_content = f"""tree {tree_sha}
parent {parent_sha}
author {author} {timestamp} -0600
committer {author} {timestamp} -0600

{commit_msg}
""".encode()

            header = f"commit {len(commit_content)}\0".encode("utf-8")
            commit_obj = header + commit_content
            sha = hashlib.sha1(commit_obj).hexdigest()

            dir_path = f".git/objects/{sha[:2]}"
            os.makedirs(dir_path, exist_ok=True)
            with open(f"{dir_path}/{sha[2:]}", "wb") as f:
                f.write(zlib.compress(commit_obj))
            print(sha)
        else:
            print("Insufficient arguments for commit-tree")

    else:
        raise RuntimeError(f"Unknown command {command}")

if __name__ == "__main__":
    main()
