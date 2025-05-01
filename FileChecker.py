import argparse


class FileChecker:
    def count_line_jumps(self, file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                line_jumps = content.count('\n')
                print(f"The file '{file_path}' has {line_jumps} line jumps.")
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def compare_files(self, file1_path, file2_path):
        try:
            with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
                content1 = file1.read()
                content2 = file2.read()
                if content1 == content2:
                    print(f"✅ The files '{file1_path}' and '{file2_path}' are identical.")
                else:
                    print(f"⚠️ The files '{file1_path}' and '{file2_path}' are different.")
        except FileNotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

