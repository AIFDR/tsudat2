# -*- coding: utf-8 -*-
"""
Test the config module.
"""

import os
import unittest
import build_urs_boundary
import tempfile

class TestBuildURS(unittest.TestCase): 
    """
    Test the config module
    """    
    def later(self):
        # Write a test bounding polygon file
        f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='test_jobs',
                                        delete=False)
        f.write('340411.932649,9073487.901013\n')
        f.write('370667.083362,9070584.314311\n')
        f.write('365297.492207,9047138.984342\n')
        f.write('335305.380468,9064154.066033\n')
        f.close()


    def test_create_urs_order(self):
        # Write a test landward boundary file
        f = tempfile.NamedTemporaryFile(suffix='.csv', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        f.write('335305.380468,9064154.066033\n')
        f.write('340411.932649,9073487.901013\n')
        f.close()
        lb_handle = f

        # Write a test interior hazard points file
        f = tempfile.NamedTemporaryFile(suffix='.csv', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        f.write('15,115.703000,-8.416670,357208.777944,9069401.572593\n')
        f.write('16,115.678000,-8.444940,354466.552432,9066266.201259\n')
        f.write('17,115.644000,-8.467730,350731.742651,9063733.143930\n')
        f.write('18,115.620000,-8.500000,348102.021732,9060155.270992\n')
        f.close()
        ihp_handle = f

        # Build output file
        urs_order = tempfile.NamedTemporaryFile(suffix='.csv', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        urs_order.close()

        build_urs_boundary.create_urs_order(lb_handle.name, ihp_handle.name,
                     urs_order.name)
        # Since I don't know what this file looks like I aren't testing it
        os.remove(lb_handle.name)
        os.remove(ihp_handle.name)
        os.remove(urs_order.name)
        
        pass


#-------------------------------------------------------------
if __name__ == "__main__":
    Suite = unittest.makeSuite(TestBuildURS,'test')
    Runner = unittest.TextTestRunner()
    Runner.run(Suite)
