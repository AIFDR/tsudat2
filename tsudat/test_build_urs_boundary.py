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

    def write_mux_file(self):
     # Write a test mux_event  file
        f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        f.write('3\n')
        f.write('flores-0000_waveheight-z-mux2 10.5\n')
        f.write('flores-0001_waveheight-z-mux2 10.5\n')
        f.write('flores-0002_waveheight-z-mux2 10.5\n')
        f.close()
        mux_event_file = f.name
        return mux_event_file
        
        
    def test_create_urs_order(self):
    
        mux_event_file = self.write_mux_file()
        
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
        #print "urs_order.name", urs_order.name
        os.remove(urs_order.name)
        
        
    def test_get_deformation(self):
       
        mux_event_file = self.write_mux_file()
        
        def_test_dir = os.path.join('.', 'deformation_test')
        deformation_folder = os.path.join(def_test_dir,
                                          'deformation_files')
        ouput_file = os.path.join(def_test_dir, 'output_deformation.txt')
        
        build_urs_boundary.get_deformation(mux_event_file, 
                                            deformation_folder, ouput_file)
        
        # Results should be tested. 
        # To do this though the answer has to be known
        
        os.remove(mux_event_file)
        
        
    def test_get_multimux(self):
    
        multimux_test_dir = os.path.join('.', 'muxfiles_test')
        multimux_dir = os.path.join(multimux_test_dir, 'muxfiles')
        output_file = os.path.join(multimux_test_dir,'generated_event_file.txt')
        event = 1
        build_urs_boundary.get_multimux(event, multimux_dir, output_file)
        # Results should be tested. 
        # To do this though the answer has to be known

    def test_get_multimuxII(self):
        multimux_test_dir = os.path.join('.', 'muxfiles_test')
        if os.environ['LOGNAME'] == '=tsudatkvm':
            # Assume we are on tsudat indo
             multimux_dir = os.path.join('var', 'tsudat', 'muxfiles')
             f_name = 'local_mux_files_generated_event_file.txt'
        else:
             multimux_dir = os.path.join(multimux_test_dir, 'muxfiles')
             f_name = 'test_mux_files_generated_event_file.txt'
        
        output_file = os.path.join(multimux_test_dir, f_name)
        event = 1
        build_urs_boundary.get_multimux(event, multimux_dir, output_file)
        # Results should be tested. 
        # To do this though the answer has to be known

        
    def test_build_urs_boundary(self):   
    
        mux_event_file = self.write_mux_file()
               
        # Write a test urs order file
        f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        f.write('index,longitude,latitude\n')
        f.write('18,115.620000,-8.500000\n')
        f.write('17,115.644000,-8.467730\n')
        f.write('16,115.678000,-8.444940\n')
        f.write('15,115.703000,-8.416670\n')
        f.close()
        urs_order_file = f.name
        
         # Get a sts output file
        f = tempfile.NamedTemporaryFile(suffix='.sts', 
                                        prefix='test_build_urs_boundary',
                                        delete=False)
        f.close()
        sts_outputfile = f.name
        
        multimux_test_dir = os.path.join('.', 'muxfiles_test')
        mux_data_folder = os.path.join(multimux_test_dir, 'muxfiles')
        
        build_urs_boundary.build_urs_boundary(
            mux_event_file, 
            sts_outputfile, 
            urs_order_file, 
            mux_data_folder)
            
        # Results should be tested. 
        # To do this though the answer has to be known
        
        os.remove(mux_event_file)
        os.remove(urs_order_file)
        os.remove(sts_outputfile)
        
    def test_build_boundary_deformation(self):  
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

        event = 1
        
        mux_data_folder = os.path.join('.', 'muxfiles_test', 'muxfiles')
        
        deformation_folder = os.path.join('.', 'deformation_test',
                                          'deformation_files')
        zip_filename = os.path.join('.', 'muxfiles_test', 'out_sts_and_def.zip')
                                          
        build_urs_boundary.build_boundary_deformation(
            lb_handle.name,
            ihp_handle.name,
            event,
            mux_data_folder, 
            deformation_folder, 
            zip_filename)
            
        # Since I don't know what this file looks like I aren't testing it
        os.remove(lb_handle.name)
        os.remove(ihp_handle.name)
                
#-------------------------------------------------------------
if __name__ == "__main__":
    Suite = unittest.makeSuite(TestBuildURS,'test')
    Runner = unittest.TextTestRunner()
    Runner.run(Suite)
