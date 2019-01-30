# -*- coding: utf-8 -*-
import re
import time


class IdWorker(object):
    def __init__(self, worker_id=1, data_center_id=2):
        self.worker_id = worker_id
        self.data_center_id = data_center_id

        self.user_agent_parser = re.compile("^[a-zA-Z][a-zA-Z\-0-9]*$")

        # stats
        self.ids_generated = 0

        # 2018/11/1
        self.twepoch = 946656000000L

        self.sequence = 0L
        self.worker_id_bits = 5L
        self.data_center_id_bits = 5L
        self.max_worker_id = -1L ^ (-1L << self.worker_id_bits)
        self.max_data_center_id = -1L ^ (-1L << self.data_center_id_bits)
        self.sequence_bits = 12L

        self.worker_id_shift = self.sequence_bits
        self.data_center_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_left_shift = self.sequence_bits + \
            self.worker_id_bits + self.data_center_id_bits
        self.sequence_mask = -1L ^ (-1L << self.sequence_bits)

        self.last_timestamp = -1L

        # Sanity check for worker_id
        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise Exception(
                "worker_id", "worker id can't be greater than %i or less than 0" % self.max_worker_id)

        if self.data_center_id > self.max_data_center_id or self.data_center_id < 0:
            raise Exception(
                "data_center_id", "data center id can't be greater than %i or less than 0" % self.max_data_center_id)

    def _time_gen(self):
        return long(int(time.time() * 1000))

    def _till_next_millis(self, last_timestamp):
        timestamp = self._time_gen()
        while last_timestamp <= timestamp:
            timestamp = self._time_gen()

        return timestamp

    def _next_id(self):
        timestamp = self._time_gen()

        if self.last_timestamp > timestamp:

            raise Exception(
                "Clock moved backwards. Refusing to generate id for %i milliseocnds" % self.last_timestamp)

        if self.last_timestamp == timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                timestamp = self._till_next_millis(self.last_timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        new_id = ((timestamp - self.twepoch) << self.timestamp_left_shift) | (self.data_center_id <<
                                                                              self.data_center_id_shift) | (self.worker_id << self.worker_id_shift) | self.sequence
        self.ids_generated += 1
        return new_id

    def _valid_user_agent(self, user_agent):
        return self.user_agent_parser.search(user_agent) is not None

    def get_worker_id(self):
        return self.worker_id

    def get_timestamp(self):
        return self._time_gen()

    def get_id(self, useragent="snowflake2017"):
        if not self._valid_user_agent(useragent):
            raise Exception("valid user agent")
        new_id = self._next_id()
        return new_id

    def get_datacenter_id(self):
        return self.data_center_id


if __name__ == '__main__':
    idworker = IdWorker()
    print idworker.get_id()
