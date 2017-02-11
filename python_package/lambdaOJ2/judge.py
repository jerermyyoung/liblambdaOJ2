from ctypes import CDLL, pointer, c_int, c_long, c_char_p, Structure
import os
from abc import ABCMeta, abstractmethod

from .consts import (COMPILERS, COMPILE_OK, COMPILE_ERROR, MAX_ERROR_MSG_LENGTH,
                     ACCEPTED, WRONG_ANSWER, TASK_STATUS, TASK_ALL_NORMAL)


class TaskResult(Structure):
    _fields_ = [("final_result", c_int),
                ("time_used", c_long),
                ("mem_used", c_long)]


class Judge(metaclass=ABCMeta):
    """
    This class implements the Python API for the C lib lambdaOJ2.
    And this class has 5 abstractmethod, to use it you have to
    inherit Judge, and implement these abstractmethod.

    * check_answer: (str * str) -> bool
    * get_sample_output_by_id: int -> str
    * get_test_input_by_id: int -> str
    * get_std_answer_by_id: int -> str
    * clear_run_space
    * clear_compile_space

    The method run is to check submitted code, the return data of
    run is alawys a 2-element tuple:
    * (COMPILE_OK : integer, [(status : integer,
                               time_used : integer, in ms,
                               mem_used : integer, in KBytes)])
    * (COMPILE_ERROR: integer, error_message : string)

    The object is initialized by a python dict object: json_obj
    The filed and type of this dict object is:
    {
      "problem_id": string,
      "submit_id": string,
      "compiler_name": string,
      "exe_file": string, (full path of the executable file generated by compiler)
      "err_log": string, (full path of the file of error message when compiling)
      "source_code": string, (full path of the code submitted),
      "sample_num": integer(the number of total test sample),
      "mem_limit": integer(the memory limit, in KBytes),
      "time_limit": integer(the time limit, in Seconds)
    }
    """

    def __init__(self, json_obj):
        self.json_obj = json_obj

        clib_lambdaOj2 = CDLL("liblambdaOJ2.so")
        self.compile_func = clib_lambdaOj2.compile
        self.run_task_func = clib_lambdaOj2.run_task

    def str_to_char_p(self, s):
        return c_char_p(bytes(s, "utf-8"))

    def compile(self):
        source_code = self.json_obj.get("source_code", "")
        exe_file = self.json_obj.get("exe_file", "")
        err_log = self.json_obj.get("err_log", "")

        compiler_name = self.json_obj.get("compiler_name", "")
        compiler = c_int(COMPILERS.get(compiler_name, -1))

        compile_result = self.compile_func(self.str_to_char_p(source_code),
                                           self.str_to_char_p(exe_file),
                                           compiler,
                                           self.str_to_char_p(err_log))

        return compile_result

    def run(self):
        if self.compile() == COMPILE_OK:
            results = (COMPILE_OK, self.run_samples())
            self.clear_compile_space()
            self.clear_run_space()
        else:
            results = (COMPILE_ERROR, self.get_compile_err_msg())
            self.clear_compile_space()
        return results

    @abstractmethod
    def clear_compile_space(self):
        return

    @abstractmethod
    def clear_run_space(self):
        return

    def get_compile_err_msg(self):
        err_log = self.json_obj.get("err_log", "")
        if os.path.exists(err_log):
            with open(err_log) as f:
                err_msg =  f.read(MAX_ERROR_MSG_LENGTH)
        else:
            err_msg = ""
        return err_msg

    def run_samples(self):
        sample_num = self.json_obj.get("sample_num", 1)
        results = [self.run_one_sample(i) for i in range(sample_num)]
        return results

    @abstractmethod
    def get_test_input_by_id(self, id):
        return

    @abstractmethod
    def get_sample_output_by_id(self, id):
        return

    @abstractmethod
    def get_std_answer_by_id(self, id):
        return

    @abstractmethod
    def check_answer(self, std_answer, submit_output):
        return

    def run_one_sample(self, id):
        exe_file = self.json_obj.get("exe_file", "")
        test_input = self.get_test_input_by_id(id)
        sample_output = self.get_sample_output_by_id(id)
        time_limit = self.json_obj.get("time_limie", 1)
        mem_limit = self.json_obj.get("mem_limit", 1024*20)

        tr = TaskResult()

        self.run_task_func(self.str_to_char_p(exe_file),
                           self.str_to_char_p(test_input),
                           self.str_to_char_p(sample_output),
                           c_int(time_limit),
                           c_int(mem_limit),
                           pointer(tr))


        if tr.final_result == TASK_ALL_NORMAL:
            std_answer = self.get_std_answer_by_id(id)
            if self.check_answer(std_answer, sample_output):
                return (ACCEPTED, tr.time_used, tr.mem_used)
            else:
                return (WRONG_ANSWER, 0, 0)
        else:
            status = TASK_STATUS.get(tr.final_result, -1)
            return (status, 0, 0)
