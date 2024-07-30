from sys import argv

from unused_dependencies import unused_dependencies

if __name__ == '__main__':
    if len(argv) < 2:
        print("Usage: python unused_dependencies.py <repo-name>")
        exit(-1)
    print(unused_dependencies(argv[1]))