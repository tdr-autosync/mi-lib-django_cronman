# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os

import mock

from cronman import utils
from cronman.tests.base import TEST_CRONMAN_DATA_DIR, BaseCronTestCase


class CronUtilsTestCase(BaseCronTestCase):
    """Tests for `cronman.utils` module"""

    def test_function_signature(self):
        """Test for `function_signature` function"""

        def func_a(a, b, c=42, d=None, *args, **kwargs):
            pass

        def func_b():
            pass

        self.assertEqual(
            utils.function_signature(func_a),
            "a, b, c=42, d=None, *args, **kwargs",
        )
        self.assertEqual(utils.function_signature(func_b), "")

    def test_function_signature_method(self):
        """Test for `function_signature` function - case: method"""

        class X(object):
            def method(self, a, b, c=42, d=None, *args, **kwargs):
                pass

        self.assertEqual(
            utils.function_signature(X.method),
            "a, b, c=42, d=None, *args, **kwargs",
        )

    def test_parse_params_empty(self):
        """Test for `parse_params` function - case: empty string"""
        self.assertEqual(utils.parse_params(""), ([], {}))

    def test_parse_params_positional(self):
        """Test for `parse_params` function - case: positional arguments"""
        self.assertEqual(
            utils.parse_params("Test, 1,4.2 ,\"A; B; C\", '386'"),
            (["Test", "1", "4.2", "A; B; C", "386"], {}),
        )

    def test_parse_params_named(self):
        """Test for `parse_params` function - case: keyword arguments"""
        self.assertEqual(
            utils.parse_params("a=Test, b=4.2 ,p_1=\"A; B; C\", TEST='386'"),
            ([], {"a": "Test", "b": "4.2", "p_1": "A; B; C", "TEST": "386"}),
        )

    def test_parse_params_mixed(self):
        """Test for `parse_params` function - case: mixed arguments"""
        self.assertEqual(
            utils.parse_params("Test, 1,4.2 ,p_1=\"A; B; C\", TEST='386'"),
            (["Test", "1", "4.2"], {"p_1": "A; B; C", "TEST": "386"}),
        )

    def test_parse_params_mixed_quoted(self):
        """Test for `parse_params` function - case: mixed arguments with 
        quoted values (comma, space)
        """
        self.assertEqual(
            utils.parse_params("\"a b\",'1,2',a='a b',b=\"1,2\""),
            (["a b", "1,2"], {"a": "a b", "b": "1,2"}),
        )

    def test_parse_params_invalid_implicit_empty_value(self):
        """Test for `parse_params` function - case: invalid params -
        implicit empty value
        """
        with self.assertRaisesMessage(
            ValueError,
            "In chars 5-11 ` TEST=`: "
            'Implicit empty value. Use explicit `""` instead.',
        ):
            utils.parse_params("Test, TEST=")

    def test_parse_params_invalid_unbalanced_parentheses(self):
        """Test for `parse_params` function - case: invalid params -
        unbalanced parentheses
        """
        with self.assertRaisesMessage(
            ValueError, 'In chars 5-12 ` TEST="`: Unbalanced parentheses.'
        ):
            utils.parse_params('Test, TEST="')

    def test_parse_params_invalid_positional_after_named_arg(self):
        """Test for `parse_params` function - case: invalid params -
        positional argument after named one
        """
        with self.assertRaisesMessage(
            ValueError,
            "In chars 13-18 `4.2 ,`: "
            "Positional argument after named arguments.",
        ):
            utils.parse_params("Test, TEST=1,4.2 ,\"A; B; C\", '386'")

    def test_parse_params_invalid_duplicated_named_arg(self):
        """Test for `parse_params` function - case: invalid params -
        duplicated named argument
        """
        with self.assertRaisesMessage(
            ValueError, "In chars 8-15 `param=2`: Duplicated named argument."
        ):
            utils.parse_params("param=1,param=2")

    def test_parse_job_spec_no_params(self):
        """Test for `parse_job_spec` function - case: no params"""
        self.assertEqual(utils.parse_job_spec("CronJob"), ("CronJob", [], {}))

    def test_parse_job_spec_valid_params(self):
        """Test for `parse_job_spec` function - case: valid params"""
        self.assertEqual(
            utils.parse_job_spec('CronJob:42,a=1, b="a: b c"'),
            ("CronJob", ["42"], {"a": "1", "b": "a: b c"}),
        )

    def test_parse_job_spec_invalid_params(self):
        """Test for `parse_job_spec` function - case: invalid params"""
        with self.assertRaisesMessage(
            ValueError, "Positional argument after named arguments."
        ):
            utils.parse_job_spec('CronJob:a=1,"test"'),

    def test_bool_param_true(self):
        """Test for `bool_param` function - case: true values"""
        self.assertTrue(utils.bool_param("1"))
        self.assertTrue(utils.bool_param("Yes"))
        self.assertTrue(utils.bool_param("y"))
        self.assertTrue(utils.bool_param("True"))
        self.assertTrue(utils.bool_param("ON"))

    def test_bool_param_false(self):
        """Test for `bool_param` function - case: false values"""
        self.assertFalse(utils.bool_param("0"))
        self.assertFalse(utils.bool_param("no"))
        self.assertFalse(utils.bool_param("N"))
        self.assertFalse(utils.bool_param("false"))
        self.assertFalse(utils.bool_param("Off"))

    def test_bool_param_undefined(self):
        """Test for `bool_param` function - case: undefined values"""
        self.assertIsNone(utils.bool_param(""))
        self.assertIsNone(utils.bool_param(None))

    def test_bool_param_no_conversion(self):
        """Test for `bool_param` function - case: no conversion"""
        self.assertTrue(utils.bool_param(True))
        self.assertFalse(utils.bool_param(False))

    def test_flag_param_explicit_value_true(self):
        """Test for `flag_param` function - case: explicit value, true"""
        self.assertTrue(utils.flag_param("yes", "f1", None))
        self.assertTrue(utils.flag_param(True, "f1", ""))

    def test_flag_param_explicit_value_false(self):
        """Test for `flag_param` function - case: explicit value, false"""
        self.assertFalse(utils.flag_param("no", "f1", ""))
        self.assertFalse(utils.flag_param(False, "f1", None))

    def test_flag_param_fallback_value_true(self):
        """Test for `flag_param` function - case: explicit value not provided -
        fallback to flags, true (flag found)
        """
        self.assertTrue(utils.flag_param(None, "f1", "f1 f2"))
        self.assertTrue(utils.flag_param(None, "f1", "-f5-f1"))
        self.assertTrue(utils.flag_param("", "f1", "f0,f1,f2"))
        self.assertTrue(utils.flag_param("", "f1", "f0;f1;f2"))

    def test_flag_param_fallback_value_false(self):
        """Test for `flag_param` function - case: explicit value not provided -
        fallback to flags, false (flag not found)
        """
        self.assertFalse(utils.flag_param(None, "f1", "f3 f2"))
        self.assertFalse(utils.flag_param(None, "f1", "-f5-f3"))
        self.assertFalse(utils.flag_param(None, "f1", ""))
        self.assertFalse(utils.flag_param(None, "f1", None))
        self.assertFalse(utils.flag_param("", "f1", "f0,f3,f2"))
        self.assertFalse(utils.flag_param("", "f1", "f0;f3;f2"))
        self.assertFalse(utils.flag_param("", "f1", ""))
        self.assertFalse(utils.flag_param("", "f1", None))

    def test_list_param_default(self):
        """Test for `list_param` function - case: default values"""
        self.assertEqual(utils.list_param("a B 42"), ["a", "B", "42"])
        self.assertEqual(utils.list_param("a\tXY\t1.5\t"), ["a", "XY", "1.5"])
        self.assertEqual(utils.list_param(""), [])

    def test_list_param_custom_integers(self):
        """Test for `list_param` function - case: customized params,
        semicolon-separated list of integers
        """
        self.assertEqual(
            utils.list_param("12; 2; 386", delimiter=";", cast=int),
            [12, 2, 386],
        )

    def test_list_param_custom_string(self):
        """Test for `list_param` function - case: customized params,
        tab-separated list of strings, keep empty items, don't strip spaces
        """
        self.assertEqual(
            utils.list_param(
                "Text 1 \tTEST\t B \t",
                delimiter="\t",
                skip_empty=False,
                strip=False,
            ),
            ["Text 1 ", "TEST", " B ", ""],
        )

    def test_list_param_custom_default_and_replace(self):
        """Test for `list_param` function - case: default and replace_map
        """
        self.assertEqual(
            utils.list_param("", default=["default"]), ["default"]
        )
        self.assertEqual(
            utils.list_param("A B X", replace_map={"X": "Y"}), ["A", "B", "Y"]
        )

    def test_ensure_dir_existing_directory(self):
        """Test for `ensure_dir` function - case: existing directory"""
        os.makedirs(TEST_CRONMAN_DATA_DIR)
        self.assertTrue(utils.ensure_dir(TEST_CRONMAN_DATA_DIR))

    def test_ensure_dir_new_directory_tree(self):
        """Test for `ensure_dir` function - case: new directory tree"""
        self.assertTrue(
            utils.ensure_dir(os.path.join(TEST_CRONMAN_DATA_DIR, "a/b/c"))
        )

    def test_ensure_dir_new_directory_failure(self):
        """Test for `ensure_dir` function - case: it's a file"""
        os.makedirs(TEST_CRONMAN_DATA_DIR)
        path = os.path.join(TEST_CRONMAN_DATA_DIR, "text.txt")
        with open(path, "a"):
            self.assertFalse(utils.ensure_dir(path))

    def test_spawn(self):
        """Test for `spawn` function"""
        with mock.patch("cronman.utils.subprocess.Popen") as mock_popen:
            type(mock_popen.return_value).pid = mock.PropertyMock(
                return_value=42
            )
            self.assertEqual(utils.spawn("ls", "-la"), 42)

    def test_execute(self):
        """Test for `execute` function"""
        path = os.path.join(TEST_CRONMAN_DATA_DIR, "execute")
        os.makedirs(path)
        with open(os.path.join(path, "aaa.txt"), "a"):
            pass
        with open(os.path.join(path, "bbb.txt"), "a"):
            pass
        result = utils.execute("ls", path)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 0)
        self.assertEqual(result.args, ("ls", path))
        self.assertEqual(result.command, "ls {}".format(path))
        self.assertEqual(
            set(result.output_text.strip().split("\n")), {"aaa.txt", "bbb.txt"}
        )

    def test_execute_pipe(self):
        """Test for `execute_pipe` function"""
        path = os.path.join(TEST_CRONMAN_DATA_DIR, "execute")
        os.makedirs(path)
        with open(os.path.join(path, "aaa.txt"), "a"):
            pass
        with open(os.path.join(path, "bbb.txt"), "a"):
            pass
        with open(os.path.join(path, "abb.txt"), "a"):
            pass
        result = utils.execute_pipe(["ls", "-A1", path], ["grep", "bb"])
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 0)
        self.assertEqual(result.args, (["ls", "-A1", path], ["grep", "bb"]))
        self.assertEqual(result.command, "ls -A1 {} | grep bb".format(path))
        self.assertEqual(
            set(result.output_text.strip().split("\n")), {"abb.txt", "bbb.txt"}
        )

    def test_execute_pipe_non_zero_return_code(self):
        """Test for `execute_pipe` function - case: non-zero return code"""
        path = os.path.join(TEST_CRONMAN_DATA_DIR, "execute")
        os.makedirs(path)
        result = utils.execute_pipe(["ls", "-A1", path], ["grep", "bb"])
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 1)

    def test_cwd_ok(self):
        """Test for `CWD` context manager - case: no exception raised"""
        path = os.path.realpath(os.path.join(TEST_CRONMAN_DATA_DIR, "cwd"))
        os.makedirs(path)
        cwd = os.getcwd()
        with utils.CWD(path):
            self.assertEqual(os.getcwd(), path)
            self.assertEqual(utils.execute("pwd").output_text.strip(), path)
        self.assertEqual(os.getcwd(), cwd)

    def test_cwd_exception(self):
        """Test for `CWD` context manager - case: exception raised"""
        path = os.path.realpath(os.path.join(TEST_CRONMAN_DATA_DIR, "cwd"))
        os.makedirs(path)
        cwd = os.getcwd()
        try:
            with utils.CWD(path):
                self.assertEqual(os.getcwd(), path)
                self.assertEqual(
                    utils.execute("pwd").output_text.strip(), path
                )
                raise RuntimeError
        except RuntimeError:
            pass
        self.assertEqual(os.getcwd(), cwd)

    @mock.patch("cronman.utils.os.environ", {"CRON_PROCESS_RESUMED": "1"})
    def test_is_cron_process_resumed_yes(self):
        """Test for `is_cron_process_resumed` function - case: yes"""
        self.assertTrue(utils.is_cron_process_resumed())

    @mock.patch("cronman.utils.os.environ", {"CRON_PROCESS_RESUMED": "0"})
    def test_is_cron_process_resumed_no(self):
        """Test for `is_cron_process_resumed` function - case: no"""
        self.assertFalse(utils.is_cron_process_resumed())

    @mock.patch("cronman.utils.os.environ", {})
    def test_is_cron_process_resumed_unset(self):
        """Test for `is_cron_process_resumed` function - case: unset (no)"""
        self.assertFalse(utils.is_cron_process_resumed())

    @mock.patch("cronman.utils.os.environ", {"CRON_PROCESS_RESUMED": ""})
    def test_is_cron_process_resumed_empty(self):
        """Test for `is_cron_process_resumed` function - case: empty (no)"""
        self.assertFalse(utils.is_cron_process_resumed())

    @mock.patch("cronman.worker.worker.CronWorker.get_pid_file")
    @mock.patch("cronman.worker.worker.CronWorker.pid_file_locked")
    def test_is_cron_job_running_default(
        self, mock_pid_file_locked, mock_get_pid_file
    ):
        """Test for `is_cron_job_running` function - case: default params"""
        mock_pid_file = mock.MagicMock()
        mock_get_pid_file.return_value = mock_pid_file
        mock_pid_file_locked.return_value = True

        class FakeCronJob(object):
            pass

        self.assertTrue(utils.is_cron_job_running(FakeCronJob))

        mock_get_pid_file.assert_called_once_with(
            cron_job_class=FakeCronJob, name="FakeCronJob", args=[], kwargs={}
        )
        mock_pid_file_locked.assert_called_once_with(mock_pid_file, 1)

    @mock.patch("cronman.worker.worker.CronWorker.get_pid_file")
    @mock.patch("cronman.worker.worker.CronWorker.pid_file_locked")
    def test_is_cron_job_running_custom(
        self, mock_pid_file_locked, mock_get_pid_file
    ):
        """Test for `is_cron_job_running` function - case: custom params"""
        mock_pid_file = mock.MagicMock()
        mock_get_pid_file.return_value = mock_pid_file
        mock_pid_file_locked.return_value = False

        class FakeCronJob(object):
            pass

        self.assertFalse(
            utils.is_cron_job_running(
                FakeCronJob,
                name="AlternativeName",
                args=[42],
                kwargs={"param": 0},
            )
        )

        mock_get_pid_file.assert_called_once_with(
            cron_job_class=FakeCronJob,
            name="AlternativeName",
            args=[42],
            kwargs={"param": 0},
        )
        mock_pid_file_locked.assert_called_once_with(mock_pid_file, 1)
