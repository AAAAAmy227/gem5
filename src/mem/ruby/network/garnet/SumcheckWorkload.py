from m5.objects.ClockedObject import ClockedObject
from m5.params import *


class SumcheckWorkload(ClockedObject):
    type = "SumcheckWorkload"
    cxx_header = "mem/ruby/network/garnet/SumcheckWorkload.hh"
    cxx_class = "gem5::ruby::garnet::SumcheckWorkload"

    events = VectorParam.String([], "validated causal event records")
    injection_buffers = VectorParam.MessageBuffer(
        [], "one outgoing protocol queue per logical endpoint"
    )
    mode = Param.String("aggregated", "logical workload variant")
    report_file = Param.String("", "completion/accounting JSON output")
    seed = Param.UInt64(1, "reproducible workload seed")
    flit_bytes = Param.UInt32(16, "configured Garnet flit size")
    watchdog_cycles = Param.Cycles(50000, "cycles without an arrival")
