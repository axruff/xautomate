from XAutomate import *
from XAnalyzer import *

automate = XAutomate(application_path='/home/ws/optic_flow/xflow',
                     settings_path='/home/ws/optic_flow/settings.xml',
                     output_path='/mnt/LSDF/tomo/ershov/spray/report/',
                     orderer=TreeOrderer(depth=2))



alpha_list = [str(x) for x in np.arange(10.0, 50.0, 5)]
sigma_list = [str(x) for x in np.arange(1.0, 5.0, 0.25)]

automate.addListParameter(name='alpha', values=alpha_list)
automate.addListParameter(name='sigma', values=sigma_list)

#-----------------------------------
# Run processing
#-----------------------------------
automate.execute(processes=12)


#-----------------------------------
# Collect and Analyze results
#-----------------------------------

# Get statistics from XAutomate results
a = XAnalyzer(stats_filename=path+'stats.txt', results_filename='results.txt')

# Plot results metrics (aee_all, aee_disc, aee_untext) depending on different automation parameters (sigma, alpha)
a.plot2D('sigma', 'alpha', 'aee_all')
a.plot2D('sigma', 'alpha', 'aee_disc')
a.plot2D('sigma', 'alpha', 'aee_untext')

# Save results in compact form as a table 
a.saveTable(filename=path+'table.txt', title=True)

# Save results as a numpy array for further analysis
a.saveNPArray(filename=path+'numpy_data.txt')