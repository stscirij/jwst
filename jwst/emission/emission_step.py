#! /usr/bin/env python

from ..stpipe import Step, cmdline
from . import emission

class EmissionStep(Step):
    """
    EmissionStep: This step currently is a no-op; it passes the input file to
    the next step unchanged.
    """


    def process(self, input_file):

        ff_a = emission.DataSet(input_file)
        output_obj = ff_a.do_all()
        output_obj.meta.cal_step.emission = 'SKIPPED' # no-op

        return output_obj


if __name__ == '__main__':
    cmdline.step_script(emission_step)
