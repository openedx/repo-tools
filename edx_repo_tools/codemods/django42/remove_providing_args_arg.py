import os
import re
import click

def remove_providing_args(root_dir):
    # Regex pattern to match the lines containing providing_args
    pattern = r"(.*)[,\s]*providing_args\s*=\s*\[.*?\](.*)"

    # Traverse all Python files in the root directory
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                updated_lines = []

                # Open the file and read its content
                with open(file_path, "r") as f:
                    lines = f.readlines()

                    # Process each line in the file
                    for line in lines:
                        # Check if the line contains providing_args
                        match = re.match(pattern, line)
                        if match:
                            # Remove the providing_args argument along with any preceding comma or whitespace
                            updated_line = match.group(1).rstrip(", \t") + match.group(2) + "\n"
                            updated_lines.append(updated_line)
                        else:
                            updated_lines.append(line)

                # Write the updated content back to the file
                with open(file_path, "w") as f:
                    f.writelines(updated_lines)


@click.command()
@click.option(
    '--root_dir', default='.',
    help="Path to root of project")
def main(root_dir):
    remove_providing_args(root_dir)
    print("Providing_args removed from the specified lines.")


if __name__ == '__main__':
    main()