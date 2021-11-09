#!/usr/bin/python3
"""
  (C) Copyright 2018-2021 Intel Corporation.

  SPDX-License-Identifier: BSD-2-Clause-Patent
"""
import re

from ior_test_base import IorTestBase
from mdtest_test_base import MdtestBase

class PerformanceTestBase(IorTestBase, MdtestBase):
    # pylint: disable=too-many-ancestors
    """Base performance class."""

    def print_performance_params(self, cmd):
        """Print performance parameters.

        Args:
            cmd (str): ior or mdtest

        """
        # Start with common parameters
        # Build a list of [PARAM_NAME, PARAM_VALUE]
        params = [
            ["TEST_NAME", self.test_id],
            ["NUM_SERVERS", len(self.hostlist_servers)],
            ["NUM_CLIENTS", len(self.hostlist_clients)],
            ["PPC", self.ppn],
            ["PPN", self.ppn]
        ]

        # Get ior/mdtest specific parameters
        cmd = cmd.lower()
        if cmd == "ior":
            params += [
                ["API", self.ior_cmd.api.value],
                ["OCLASS", self.ior_cmd.dfs_oclass.value],
                ["XFER_SIZE", self.ior_cmd.transfer_size.value],
                ["BLOCK_SIZE", self.ior_cmd.block_size.value],
                ["SW_TIME", self.ior_cmd.sw_deadline.value],
                ["CHUNK_SIZE", self.ior_cmd.dfs_chunk.value]
            ]
        elif cmd == "mdtest":
            params += [
                ["API", self.mdtest_cmd.api.value],
                ["OCLASS", self.mdtest_cmd.dfs_oclass.value],
                ["DIR_OCLASS", self.mdtest_cmd.dfs_dir_oclass.value],
                ["SW_TIME", self.mdtest_cmd.stonewall_timer.value],
                ["CHUNK_SIZE", self.mdtest_cmd.dfs_chunk.value]
            ]
        else:
            self.fail("Invalid cmd: {}".format(cmd))

        # Print and align all parameters in the format:
        # PARAM_NAME : PARAM_VALUE
        self.log.info("PERFORMANCE PARAMS START")
        max_len = max([len(param[0]) for param in params])
        for param in params:
            self.log.info("{:<{}} : {}".format(param[0], max_len, param[1]))
        self.log.info("PERFORMANCE PARAMS END")

    def print_system_status(self):
        """TODO"""
        pass

    def verify_oclass_compat(self, oclass):
        """Verify an object class is compatible with the number of servers.

        TODO move this to a lower level in the framework.

        Args:
            oclass (str): The object class. Assumed to be valid.

        """
        patterns = [
            "EC_([0-9]+)P([0-9])+",
            "RP_([0-9]+)"
        ]
        for pattern in patterns:
            match = re.findall(pattern, oclass)
            if match:
                # Sum all groups ()
                min_servers = sum(int(n) for n in match[0])
                if len(self.hostlist_clients) < min_servers:
                    self.fail("Need at least {} servers for oclass {}".format(min_servers, oclass))
                break

    def run_performance_ior(self, write_flags=None, read_flags=None, namespace=None):
        """Run an IOR performance test.

        Args:
            namespace (str, optional): namespace for IOR parameters in the yaml.
                Defaulits to None, which uses default IOR namespace.

        """
        # Always get processes and ppn from the default ior namespace.
        # Needed to avoid conflict between ior and mdtest test bases.
        self.processes = self.params.get("np", '/run/ior/client_processes/*')
        self.ppn = self.params.get("ppn", '/run/ior/client_processes/*')

        if namespace is None:
            write_flags = self.params.get("write_flags", ior_cmd.namespace)
            read_flags = self.params.get("read_flags", ior_cmd.namespace)
        else:
            self.ior_cmd.namespace = namespace
            self.ior_cmd.get_params(self)
            write_flags = self.params.get("write_flags", namespace)
            read_flags = self.params.get("read_flags", namespace)
        if write_flags is None:
            self.fail("write_flags not found in config")
        if read_flags is None:
            self.fail("read_flags not found in config")

        self.print_performance_params("ior")

        self.verify_oclass_compat(self.ior_cmd.dfs_oclass.value)

        self.log.info("Running IOR write")
        self.ior_cmd.flags.update(write_flags)
        self.run_ior_with_pool()

        self.log.info("Running IOR read")
        self.ior_cmd.flags.update(read_flags)
        self.ior_cmd.sw_wearout.update(None)
        self.ior_cmd.sw_deadline.update(None)
        self.run_ior_with_pool(create_cont=False)

    def run_performance_mdtest(self, namespace=None):
        """Run an MdTest performance test.

        Args:
            namespace (str, optional): namespace for MdTest parameters in the yaml.
                Defaulits to None, which uses default MdTest namespace.

        """
        # Always get processes and ppn from the default mdtest namespace.
        # Needed to avoid conflict between ior and mdtest test bases.
        self.processes = self.params.get("np", '/run/mdtest/client_processes/*')
        self.ppn = self.params.get("ppn", '/run/mdtest/client_processes/*')

        if namespace is not None:
            self.mdtest_cmd.namespace = namespace
            self.mdtest_cmd.get_params(self)

        self.print_performance_params("mdtest")

        self.verify_oclass_compat(self.mdtest_cmd.dfs_oclass.value)
        self.verify_oclass_compat(self.mdtest_cmd.dfs_dir_oclass.value)

        self.log.info("Running MDTEST")
        self.execute_mdtest()