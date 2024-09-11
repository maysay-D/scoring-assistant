import subprocess
import zipfile
from pathlib import Path

from astyle_py import Astyle
from chardet import detect


class Answer:
    def __init__(self, file_path: Path, task: dict) -> None:
        self.file_path: Path = file_path
        self.code_txt: str = ""
        self.result_txt: str = ""
        self.task_name: str = task["name"]
        self.task_lang: str = task["lang"]
        self.inputs: list[dict[str, str]] = task.get("inputs", [{"input": ""}])
        self.args: list[dict[str, list[str]]] = task.get("args", [{"arg": []}])
        self.file_list: list[str] = [self.task_name]

    def __str__(self) -> str:
        return (
            f"{self.file_path = }\n"
            f"{self.code_txt = }\n"
            f"{self.result_txt = }\n"
            f"{self.task_name = }\n"
            f"{self.task_lang = }\n"
            f"{self.inputs = }\n"
            f"{self.args = }\n"
            f"{self.file_list = }\n"
        )

    def get_code(self) -> str:
        """
        taskの言語に合わせて中身を取得
        jar,zipの場合は中身を展開する
        """
        try:
            if self.task_lang in ["jar", "zip"]:
                self.code_txt, f_list = unpack_files(self.file_path)
                self.file_list += f_list
            else:
                with open(self.file_path, mode="rb") as f:
                    b = f.read()
                    enc = detect(b)["encoding"]
                    if enc is None:
                        enc = "utf-8"
                    self.code_txt = b.decode(enc, errors="backslashreplace")
                    if self.task_lang == "java":
                        self.code_txt = formating(self.code_txt)
        except Exception as e:
            self.code_txt = (
                "Open Error : " + str(self.file_path) + "\n手動で確認してください"
            )
            print(self.file_path, e)
        self.code_txt = self.code_txt.strip()
        return self.code_txt

    def execute(self):
        proj_dir_abs_path = Path(__file__).parent
        jdk_abs_path = Path(proj_dir_abs_path, "tools", "jdk-21", "bin", "java.exe")
        if self.task_lang == "jar":
            cmd = [jdk_abs_path, "-jar", self.file_path]
        elif self.task_lang == "java":
            cmd = [jdk_abs_path, self.file_path]
        else:
            return

        for arg in self.args if self.args else [{"arg": []}]:
            arg_v: list[str] = arg["arg"]
            for inp in self.inputs if self.inputs else [{"input": ""}]:
                input_b: bytes = inp["input"].encode()
                try:
                    result = subprocess.run(
                        args=cmd + arg_v,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        input=input_b,
                    )
                    result_b: bytes = result.stdout
                    enc: str = detect(result_b)["encoding"] or "utf-8"
                    result = result_b.decode(enc, errors="backslashreplace")
                    self.result_txt += (
                        f"{' TEST CASE ':=^70}\n"
                        f"args  = {arg_v}\n\n"
                        f"input ↓ \n\"\"\"\n{input_b.decode()}\n\"\"\"\n"
                        f"{' RESULT ':=^70}\n"
                        f"{result.strip()}\n\n"
                    )
                except Exception as e:
                    self.result_txt += f"Exec Error : 手動で確認してください\n{e}\n"
        self.result_txt = self.result_txt.strip()
        return self.result_txt


def formating(code: str):
    """
    Artistic StyleによるJavaとCのフォーマットを行う。
    toolsディレクトリにあるexeを利用
    """
    try:
        formatter = Astyle("3.4.7")
        formatter.set_options("--style=google --delete-empty-lines --indent=spaces=2")
        res_code = formatter.format(code)
        return res_code.strip()
    except Exception:
        return code


def unpack_files(file_path, file_encoding=None):
    texts: str = ""
    file_list: list[str] = []
    text = ""
    with zipfile.ZipFile(file_path, metadata_encoding=file_encoding) as zf:
        for zip_info in zf.infolist():
            if zip_info.filename.endswith((".java", ".txt")):
                text = ""
                # ファイルのバイトデータを読み込んでテキストに変換する
                b = zf.read(zip_info)
                enc: str | None = detect(b)["encoding"]
                if enc is None:
                    text += "文字コードの推定に失敗しました。一部をエスケープシーケンスで置き換えました。"
                    enc = "utf-8"
                text += formating(b.decode(enc, errors="backslashreplace").strip())
                texts += f"{Path(zip_info.filename).name:-^70}\n{text}\n\n"
                file_list.append(Path(zip_info.filename).name)

    return texts.strip() if len(text) > 0 else "javaファイル無し", file_list


if __name__ == "__main__":
    res = formating(
        """
            public class ArrayTest {
            public static void main(String[] args){
            int[] array = new int[10];

                for(int i = 0; i < array.length; i++){
            array[i] = (i+1)*(i+1);
                }


                for(int i = array.length - 1; i >=0; i--)
                {
                            System.out.println(array[i]);
                }
            }
            }
            """
    )
    print(res)
