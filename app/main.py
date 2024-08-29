import sys
import os
import zlib
import hashlib

def create_blob_entry(path:str, write=True):
    with open(path,"rb") as f:
        data = f.read()
    header = f"blob {len(data)}\0".encode("utf-8")
    store = header + data
    sha = hashlib.sha1(store).hexdigest()
    if write:
        os.makedirs(f".git/objects/{sha[:2]}", exist_ok=True)
        with open(f".git/objects/{sha[:2]}/{sha[2:]}", "wb") as f:
            f.write(zlib.compress(store))
    return sha


def write_tree(path:str):
    if os.path.isfile(path):
        return create_blob_entry(path)
    contents = sorted(
        os.listdir(path),
        key = lambda x: x if os.path.isfile(os.path.join(path,x)) else f"{x}/",
    )
    s = b""
    for item in contents:
        if item == ".git":
            continue
        full = os.path.join(path, item)
        if os.path.isfile(full):
            s += f"100644 {item}\0".encode()
        else:
            s += f"40000 {item}\0".encode()
        sha1 = int.to_bytes(int(write_tree(full), base=16),length=20,byteorder="big")
        s += sha1
    s = f"tree {len(s)}\0".encode() + s
    sha1 = hashlib.sha1(s).hexdigest()
    os.makedirs(f".git/objects/{sha1[:2]}", exist_ok=True)
    with open(f".git/objects/{sha1[:2]}/{sha1[2:]}", "wb") as f:
        f.write(zlib.compress(s))
    return sha1
    

def main():
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")
    elif command == "cat-file":
        if sys.argv[2] == "-p":
            blob_sha = sys.argv[3]
            with open(f".git/objects/{blob_sha[:2]}/{blob_sha[2:]}","rb") as f:
                raw = zlib.decompress(f.read())
                _, content = raw.split(b"\0", maxsplit=1)
                print(content.decode("utf-8"), end="")
    elif command == "hash-object":
        if sys.argv[2] == "-w":
            file_name = sys.argv[3]
            with open(file_name, "rb") as f:
                file_content = f.read()
            header = f"blob {len(file_content)}\x00"
            store = header.encode("ascii") + file_content
            sha = hashlib.sha1(store).hexdigest()
            git_path = os.path.join(os.getcwd(), ".git/objects")
            os.mkdir(os.path.join(git_path, sha[0:2]))
            with open(os.path.join(git_path, sha[0:2], sha[2:]), "wb") as f:
                f.write(zlib.compress(store))
            print(sha, end="")
    elif command == "ls-tree":
        if sys.argv[2] == "--name-only":
            hash = sys.argv[3]
            with open(f".git/objects/{hash[:2]}/{hash[2:]}","rb") as f:
                data = zlib.decompress(f.read())
                _, binary_data = data.split(b"\x00", maxsplit=1)
                while binary_data:
                    mode, binary_data = binary_data.split(b"\x00", maxsplit=1)
                    _, name = mode.split()
                    binary_data = binary_data[20:]
                    print(name.decode("utf-8"))
    elif command == "write-tree":
        print(write_tree("./"))
    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
