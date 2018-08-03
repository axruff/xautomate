import matplotlib.pyplot as plt
import numpy as np
import os
import math

# stats
# |-run
# |-param_values
# |  |-v_1
# |  |-v_N
# |-stats_values
#    |-s_1_pair
#    |  |-name_index
#    |  |-value
#    |-s_N_pair
#       |-name_index
#       |-value

class XAnalyzer(object):
    PRECISION = 4

    def __init__(self, stats_filename, results_filename):
        self._metric_names = []
        self._stats = []
        with open(stats_filename, 'r') as stats_file:
            self._param_names = eval(stats_file.readline())
            for line in stats_file:
                prefix, status, path, param_values = eval(line)
                if status == 'OK':
                    stats_path = os.path.dirname(stats_filename)
                    results_path = os.path.normpath(os.path.join(stats_path, path, 
                                                                 prefix + '_' + results_filename))
                    if not os.path.exists(results_path):
                        print 'ERROR! Cannot find a log file', results_path, 'for the run', prefix
        		plt.show()
                        continue
                    with open(results_path, 'r') as results_file:
                        run_stats = []
                        for line in results_file:
                            pair = line.split()
                            if pair[0] not in self._metric_names:
                                self._metric_names.append(pair[0])
                            run_stats.append((self._metric_names.index(pair[0]), pair[1]))
                        self._stats.append((prefix, param_values, tuple(run_stats)))
        self._stats = sorted(self._stats, key=lambda stat: int(stat[0]))
        self._param_values = []
        print 'There are:'
        for p in range(len(self._param_names)):
            self._param_values.append(list(set((s[1][p] for s in self._stats))))
            self._param_values[p] = sorted(self._param_values[p], key=float)
            print '', len(self._param_values[p]), 'values of %s:' % self._param_names[p], '\t'
            print ', '.join(map(lambda x: str(round(float(x), XAnalyzer.PRECISION)), self._param_values[p]))
        print ' Available metrics:\n', ', '.join(map(str, self._metric_names))
        print 
        self._np_array = self._createMultiArray()

    def _createMultiArray(self):
        shape = []
        for values in self._param_values:
            shape.append(len(values))
        shape.append(len(self._metric_names))
        array = np.zeros(tuple(shape))

        for stat in self._stats:
            p_indices = []
            for i, param in enumerate(stat[1]):
                p_indices.append(self._param_values[i].index(param))
            for i in range(len(self._metric_names)):
                s_ind, value = stat[2][i]
                indices = tuple(p_indices) + (s_ind,)
                array[indices] = value
        return array
    
    def saveTable(self, filename, title=True, separator='\t'):
        with open(filename, 'w') as f:
            if title:
                header = separator.join(['run'] + [p for p in self._param_names] + 
                                        [s for s in self._metric_names])
                f.write(header + '\n')
            for stats in self._stats:
                line = separator.join([stats[0]] + 
                                      [str(round(float(p), XAnalyzer.PRECISION)) for p in stats[1]] +
                                      [pair[1] for pair in stats[2]])
                f.write(line + '\n')

    def saveNPArray(self, filename):
        path, ext = os.path.splitext(filename)
        if not ext or ext == '.npy' or ext == '.npz':
            ext = '.txt'
        with open(path + ext, 'w') as f:
            f.write(repr(self._param_names) + '\n')
            f.write(repr(self._param_values) + '\n')
            f.write(repr(self._metric_names) + '\n')
        np.save(path, self._np_array)

    def _checkParametersAndDimensions(self, dimensions, params, metrics):
        if len(self._np_array.shape) != dimensions + 1:
            print 'Error. Data dimensionality does not match plot dimensions.'
            return False 
        if not set(params) <= (set(self._param_names)) or \
                not set(metrics) <= (set(self._metric_names)):
            print 'Error. Wrong parameter oder metric names.'
            print ' Parameters:\t', ', '.join(set(params) - set(self._param_names)) 
            print ' Metrics:\t', ', '.join(set(metrics) - set(self._metric_names))
            return False
        return True

    def _checkSliceValueIndex(self, slice_index, slice_value_index):
        if slice_value_index not in range(len(self._param_values[slice_index])):
            print 'Error. Wrong value index %s.' % slice_value_index
            return False
        return True

    def _2DPlot(self, _plt, data, x_ind, y_ind, metric_name):
        PRECISION = 3        
        fig, ax = _plt.subplots()
        cax = ax.imshow(data, interpolation='nearest', vmin=data.min(),
                   vmax=data.max(), origin='lower', cmap = 'RdYlGn_r')
        ax.set_title(metric_name)
        cbar = fig.colorbar(cax)
        _plt.grid(False)
        _plt.xlabel(self._param_names[x_ind])
        _plt.xticks(range(len(self._param_values[x_ind])),
                   map(lambda x: round(float(x), PRECISION), self._param_values[x_ind]))
        _plt.ylabel(self._param_names[y_ind])
        _plt.yticks(range(len(self._param_values[y_ind])),
                   map(lambda x: round(float(x), PRECISION), self._param_values[y_ind]))               

    def plot2D(self, param_x, param_y, metric_name):
        PRECISION = 3
        if not self._checkParametersAndDimensions(2, (param_x, param_y), (metric_name,)):
            return
        x_ind = self._param_names.index(param_x)
        y_ind = self._param_names.index(param_y)
        m_ind = self._metric_names.index(metric_name)
        data = self._np_array[..., m_ind]
        if (x_ind < y_ind):
            data = data.T
        self._2DPlot(plt, data, x_ind, y_ind, metric_name)
        plt.show()

    def plot2DMany(self, param_x, param_y, cols, *metric_names):
        PRECISION = 3
        if not self._checkParametersAndDimensions(2, (param_x, param_y), metric_names):
            return
        x_ind = self._param_names.index(param_x)
        y_ind = self._param_names.index(param_y)
        rows = len(metric_names) / cols + (1 if len(metric_names) % cols > 0 else 0)

        for i, metric_name in enumerate(metric_names):
            s_ind = self._metric_names.index(metric_name)
            data = np.zeros((len(self._param_values[x_ind]), len(self._param_values[y_ind])))
            data = self._np_array[..., s_ind]
            if (x_ind < y_ind):
                data = data.T

            plt.subplot(rows, cols, i + 1)
            plt.title(metric_name)
            plt.imshow(data, interpolation='nearest', vmin=data.min(),
                       vmax=data.max(), origin='lower')
            plt.colorbar()
            plt.grid(True)
            plt.xlabel(param_x)
            plt.xticks(range(len(self._param_values[x_ind])),
                       map(lambda x: round(float(x), PRECISION), self._param_values[x_ind]),
                       rotation=70)
            plt.ylabel(param_y)
            plt.yticks(range(len(self._param_values[y_ind])),
                       map(lambda x: round(float(x), PRECISION), self._param_values[y_ind]))
        plt.show()
    
    def plot2DSlice(self, param_x, param_y, slice_param, slice_value_index, metric_name):
        if not self._checkParametersAndDimensions(3, (param_x, param_y, slice_param), (metric_name,)):
            return
        x_ind = self._param_names.index(param_x)
        y_ind = self._param_names.index(param_y)
        s_ind = self._param_names.index(slice_param)
        m_ind = self._metric_names.index(metric_name)
        if not self._checkSliceValueIndex(s_ind, slice_value_index):
            return    
        print 'Slice parameter', slice_param, '=', self._param_values[s_ind][slice_value_index]
        #slice_param_value = self._param_values[s_ind][slice_value_index]
	indices = (slice_value_index if s_ind == 0 else Ellipsis,
                   slice_value_index if s_ind == 1 else Ellipsis,
                   slice_value_index if s_ind == 2 else Ellipsis,
                   m_ind)
        data = self._np_array[indices]
        if (x_ind < y_ind):
            data = data.T
        self._2DPlot(plt, data, x_ind, y_ind, metric_name)
        plt.show()

    def show2DSliceStat(self, slice_param, slice_value_index, metric_name):
        #if not self._checkParametersAndDimensions(3, (param_x, param_y, slice_param), (metric_name,)):
        #    return
        s_ind = self._param_names.index(slice_param)
        m_ind = self._metric_names.index(metric_name)
        if not self._checkSliceValueIndex(s_ind, slice_value_index):
            return    
        #print 'Slice parameter', slice_param, '=', self._param_values[s_ind][slice_value_index]
        
        slice_param_value = self._param_values[s_ind][slice_value_index]
	indices = (slice_value_index if s_ind == 0 else Ellipsis,
                   slice_value_index if s_ind == 1 else Ellipsis,
                   slice_value_index if s_ind == 2 else Ellipsis,
                   m_ind)
        data = self._np_array[indices]
        #if (x_ind < y_ind):
        #    data = data.T

	if s_ind == 0:
		i1,i2 = 1, 2	
	if s_ind == 1:
		i1,i2 = 0, 2	
	if s_ind == 2:
		i1,i2 = 0, 1	
	
	p1_name = self._param_names[i1]
	p2_name = self._param_names[i2]
	min_value = np.argmin(data)
	#print min_value
	#print data.shape
	
	#print i1, i2
	#print self._param_values
	p1_value = self._param_values[i1][int(min_value / data.shape[1])]
	p2_value = self._param_values[i2][min_value % data.shape[1]]

	#print slice_param, slice_param_value, np.min(data), p1_name, p1_value, p2_name, p2_value
	print np.min(data), p1_name, p1_value, p2_name, p2_value

    def plot2DSliceMany(self, param_x, param_y, slice_param, slice_value_index, cols, *metric_names):
        PRECISION = 3
        if not self._checkParametersAndDimensions(3, (param_x, param_y), metric_names):
            return
        x_ind = self._param_names.index(param_x)
        y_ind = self._param_names.index(param_y)
        s_ind = self._param_names.index(slice_param)
        if not self._checkSliceValueIndex(s_ind, slice_value_index):
            return    
        print 'Slice parameter', slice_param, '=', self._param_values[s_ind][slice_value_index]
        indices = (slice_value_index if s_ind == 0 else Ellipsis,
                   slice_value_index if s_ind == 1 else Ellipsis,
                   slice_value_index if s_ind == 2 else Ellipsis)
        rows = len(metric_names) / cols + (1 if len(metric_names) % cols > 0 else 0)
        plt.suptitle(slice_param + ' = ' + self._param_values[s_ind][slice_value_index], fontsize=20)
        for i, metric_name in enumerate(metric_names):
            m_ind = self._metric_names.index(metric_name)
            data = np.zeros((len(self._param_values[x_ind]), len(self._param_values[y_ind])))
            data = self._np_array[indices + (m_ind,)]
            if (x_ind < y_ind):
                data = data.T
            plt.subplot(rows, cols, i + 1)
            plt.title(metric_name)
            plt.imshow(data, interpolation='nearest', vmin=data.min(),
                       vmax=data.max(), origin='lower')
            plt.colorbar()
            plt.grid(True)
            plt.xlabel(param_x)
            plt.xticks(range(len(self._param_values[x_ind])),
                       map(lambda x: round(float(x), PRECISION), self._param_values[x_ind]),
                       rotation=70)
            plt.ylabel(param_y)
            plt.yticks(range(len(self._param_values[y_ind])),
                       map(lambda x: round(float(x), PRECISION), self._param_values[y_ind]))
        plt.show()

    def plot1D(self, param, metric_name):
        if not self._checkParametersAndDimensions(1, (param,), (metric_name,)):
            return
        p_ind = self._param_names.index(param)
        m_ind = self._metric_names.index(metric_name)
        data = self._np_array[..., m_ind]
        ticks = self._param_values[p_ind]  
        plt.title(metric_name)
        plt.xlabel(param)
        plt.plot(ticks, data, 'o-')
        plt.show()

    def plot1DMany(self, param, cols, *metric_names):
        if not self._checkParametersAndDimensions(1, (param,), metric_names):
            return        
        p_ind = self._param_names.index(param)
        ticks = self._param_values[p_ind]  
        rows = len(metric_names) / cols + (1 if len(metric_names) % cols > 0 else 0)
        for i, stat_name in enumerate(metric_names):
            m_ind = self._metric_names.index(stat_name)
            data = self._np_array[..., m_ind]
            plt.subplot(rows, cols, i + 1)
            plt.title(stat_name)
            plt.xlabel(param)
            plt.plot(ticks, data, 'o-')
        plt.show()

    def plot1DSlice(self, param, slice_param, slice_value_index, metric_name):
        if not self._checkParametersAndDimensions(2, (param, slice_param), (metric_name,)):
            return
        p_ind = self._param_names.index(param)
        s_ind = self._param_names.index(slice_param)
        m_ind = self._metric_names.index(metric_name)
        if not self._checkSliceValueIndex(s_ind, slice_value_index):
            return    
        print 'Slice parameter', slice_param, '=', self._param_values[s_ind][slice_value_index]
        indices = (slice_value_index if s_ind == 0 else Ellipsis,
                   slice_value_index if s_ind == 1 else Ellipsis,
                   m_ind)
        data = self._np_array[indices]
        ticks = self._param_values[p_ind]
        plt.suptitle(slice_param + ' = ' + self._param_values[s_ind][slice_value_index], fontsize=20)  
        plt.title(metric_name)
        plt.xlabel(param)
        plt.plot(ticks, data, 'o-')
        plt.show()

    def plot1DSliceMany(self, param, slice_param, slice_value_index, cols, *metric_names):
        if not self._checkParametersAndDimensions(2, (param, slice_param), metric_names):
            return       
        p_ind = self._param_names.index(param)
        s_ind = self._param_names.index(slice_param)
        if not self._checkSliceValueIndex(s_ind, slice_value_index):
            return    
        print 'Slice parameter', slice_param, '=', self._param_values[s_ind][slice_value_index]        
        indices = (slice_value_index if s_ind == 0 else Ellipsis,
                   slice_value_index if s_ind == 1 else Ellipsis)
        ticks = self._param_values[p_ind]  
        rows = len(metric_names) / cols + (1 if len(metric_names) % cols > 0 else 0)
        plt.suptitle(slice_param + ' = ' + self._param_values[s_ind][slice_value_index], fontsize=20)
        for i, stat_name in enumerate(metric_names):
            m_ind = self._metric_names.index(stat_name)
            data = self._np_array[indices + (m_ind, )]
            plt.subplot(rows, cols, i + 1)
            plt.title(stat_name)
            plt.xlabel(param)
            plt.plot(ticks, data, 'o-')
        plt.show()

############################ MAIN ############################

if __name__ == '__main__':

    path = '/mnt/tomoraid-LSDF/tomo/ershov/syris/output/methods/6_full/'

    a = XAnalyzer(stats_filename=path+'stats.txt',
                  results_filename='results.txt')
    a.saveTable(filename=path+'table.txt', title=True)
    a.saveNPArray(filename=path+'numpy_data.txt')
    #a.plot1D('alpha', 'aee_all')
    
    #a.plot1DMany('alpha', 3,
    #     'aee_all','opp','dev',
    #     'coll_avg','fbd','occ_avg')

    #a.plot1DSliceMany('deriv', 'num', 0,2, 'aee_all', 'aee_disc')
    #a.plot1DSliceMany('deriv', 'num', 1,2, 'aee_all', 'aee_disc')
    #a.plot1DSliceMany('deriv', 'num', 2,2, 'aee_all', 'aee_disc')
    #a.plot1DSliceMany('deriv', 'num', 3,2, 'aee_all', 'aee_disc')
    #a.plot1DSliceMany('alpha', 'sigma', 2, 5,
    #     'aee_all','aee_disc','aee_untext','amp_avg','amp_max',
    #     'R0.5_all','R0.5_disc','R0.5_untext','R1.0_all','R1.0_disc',
    #     'R1.0_untext','R2.0_all','R2.0_disc','R2.0_untext')

    #a.plot2D('sigma', 'alpha', 'aee_all')

    # a.plot2DMany('alpha','sigma', 5, 
    #     'aee_all','aee_disc','aee_untext','amp_avg','amp_max',
    #     'R0.5_all','R0.5_disc','R0.5_untext','R1.0_all','R1.0_disc',
    #     'R1.0_untext','R2.0_all','R2.0_disc','R2.0_untext'
     
    #a.plot2DMany('num','deriv', 3, 
    #     'aee_all','aee_disc','aee_untext')
     
    #print 'aee_all' 
    #a.show2DSliceStat('num', 0, 'aee_all')
    #a.show2DSliceStat('num', 1, 'aee_all')
    #a.show2DSliceStat('num', 2, 'aee_all')
    #a.show2DSliceStat('num', 3, 'aee_all')

    #a.show2DSlice('num', 0, 'aee_all')
    #print ''
	
    #a.show2DSliceStat('num', 0, 'aee_disc')
    #a.show2DSliceStat('num', 1, 'aee_disc')
    #a.show2DSliceStat('num', 2, 'aee_disc')
    #a.show2DSliceStat('num', 3, 'aee_disc')
    
    #print ''
    #a.show2DSliceStat('num', 0, 'aee_untext')
    #a.show2DSliceStat('num', 1, 'aee_untext')
    #a.show2DSliceStat('num', 2, 'aee_untext')
    #a.show2DSliceStat('num', 3, 'aee_untext')
    
    #print ''
    #a.show2DSliceStat('num', 0, 'R1.0_all')
    #a.show2DSliceStat('num', 1, 'R1.0_all')
    #a.show2DSliceStat('num', 2, 'R1.0_all')
    #a.show2DSliceStat('num', 3, 'R1.0_all')

    #print ''
    #a.show2DSliceStat('num', 0, 'aae')
    #a.show2DSliceStat('num', 1, 'aae')
    #a.show2DSliceStat('num', 2, 'aae')
    #a.show2DSliceStat('num', 3, 'aae')
 
    #a.plot2DSliceMany('sigma','alpha', 'beta1', 1, 5, 
    #    'aee_all','aee_disc','aee_untext','amp_avg','amp_max',
    #     'R0.5_all','R0.5_disc','R0.5_untext','R1.0_all','R1.0_disc',
    #     'R1.0_untext','R2.0_all','R2.0_disc','R2.0_untext')
     
    #os.system('pause')
