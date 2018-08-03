
"""
Copyright 2013-2018. Karlsruhe Institute of Technology

Automate data evaluation and benchmarking of algorithms on different parameters

XAutomate class runs an application (program, script, etc) using parametrized input.
The results of each computation (data, tables, images) are saved in the folder with a structured name.
Name is derived from the corresponding parameters and can be structured using TreeOrderer class.

The target application should support parametrization via:
- command line
- setting file

Target application can output results, which might be then collected by XAnalyzer class.

---------------
Usage examples:
---------------

# Run 'my.app' using parametrized settings file, save all results in the same folder '/results/' 
automate = XAutomate(application_path='/programs/my_app',
                     settings_path='/settings.xml',
                     output_path='/results/',
                     )

# Run 'process.py' with parametrized command line parameters. 
# Output results from 2 parameters to folders named after each parameter and its value: '/results/alpha-10/sigma-5/'                         
automate = XAutomate(application_path='/scripts/process.py',
                     command='alpha=${alpha} sigma=${sigma}',
                     output_path='/results/',
                     orderer=TreeOrderer(depth=2))
"""

import os
import re
import string
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from decimal import Decimal
from multiprocessing.pool import ThreadPool
from string import Template

class XAutomate(object):
    def __init__(self, application_path, settings_path, output_path, orderer):
        """Setup automation class.

    Args:
        application_path: Full path and name to the application or script
        settings_path: Full path and name to the settings file
        output_path: path of the results
        orderer: TreeOrder class to control how the results are structured into folders. TreeOrder(depth=0): same folder; TreeOrder(depth=2): 2-level subfolders 

    """
        self._application_path = application_path
        self._settings_path = settings_path
        self._output_path = output_path
        self._parameters = []
        self._fixed_parameters = {}
        self._orderer = orderer
        # file and directory existence
        if not os.path.exists(self._settings_path) or not os.path.isfile(self._settings_path):
            sys.exit('Terminated. Settings file \'' + self._settings_path + '\' is not found.')
        if not os.path.exists(self._application_path) or not os.path.isfile(self._application_path):
            sys.exit('Terminated. Application file \'' + self._application_path + '\' is not found.')
        if not os.path.exists(self._output_path) or not os.path.isdir(self._output_path):
                try:
                    os.makedirs(self._output_path)
                except OSError as e:
                    sys.exit('Terminated. Cannot create directory \'' + self._output_path +'\'.')
 
    def addParameter(self, parameter):
        self._parameters.append(parameter)

    def addListParameter(self, name, values):
        self._parameters.append(ListParameter(name, values))

    def addProgressionParameter(self, name, base, ratio, u_range):
        self._parameters.append(ProgressionParameter(name, base, ratio, u_range))

    def addExponentialParameter(self, name, base, u_range):
        self._parameters.append(ExponentialParameter(name, base, u_range))

    def addLinearParameter(self, name, start, stop, step):
        self._parameters.append(LinearParameter(name, start, stop, step))

    def addStringNumberParameter(self, name, length, u_range):
        self._parameters.append(StringNumberParameter(name, length, u_range))

    def addFixedParameters(self, **dictionary):
        self._fixed_parameters.update(dictionary)

    def _combinations(self, parameters, combination=[]):
        for value in parameters[0]:
            new_combination = combination[:]
            new_combination.append((parameters[0].name, value))
            if len(parameters) != 1:
                for _combination in self._combinations(parameters[1:], new_combination):
                    yield _combination
            else:
                yield new_combination

    def _validateTemplateAndParameters(self, settings):
        # empty parameters
        has_no_values = False
        for parameter in self._parameters:
            if len([value for value in parameter]) == 0:
                print 'WARNING: Parameter \'' + parameter.name + '\' has no values.'      
                has_no_values = True
        if has_no_values:
            sys.exit('Terminated. Some parameters have no values.')
        # difference between template and specified parameters
        pattern = re.compile(r'\$\{\w+}')
        template_parameters = [p[2:-1] for p in pattern.findall(settings)]
        specified_parameters = [p.name for p in self._parameters]
        fixed_parameters = self._fixed_parameters.keys()
        
        duplicated = [key for key, value in Counter(specified_parameters).items() if value > 1]
        if len(duplicated) > 0:
            sys.exit('Terminated. Specified parameters have duplicated parameter names: ' + \
                str(duplicated))
        
        both_types = set(specified_parameters) & set(fixed_parameters)
        if len(both_types) > 0:
            sys.exit('Terminated. Parametes ' + str(list(both_types)) + ' cannot be ' + \
                'specified and fixed at the same time.')         

        non_specified = set(template_parameters) - set(specified_parameters + fixed_parameters)
        if len(non_specified) > 0:
            sys.exit('Terminated. Parametes ' + str(list(non_specified)) + ' have to be ' + \
                'specified.')

        superfluous = set(specified_parameters + fixed_parameters) - set(template_parameters)
        if len(superfluous) > 0:
            sys.exit('Terminated. There are no parametes ' + str(list(superfluous)) + ' in the ' \
                'template file.')

    def _read_settings(self):
        try:
            with open(self._settings_path, 'r') as settings_file:
                settings = settings_file.read()
                return settings
        except IOError as e:
            sys.exit('Terminated. Cannot read settings file \'' + self._settings_path +'\'.')
   
    def _run(self, (iteration, parameters)):
        temp_dir = self._orderer.getLocalTempFolder()
        setting_filename = self._orderer.getSettingFilename()
        settings_path = os.path.join(temp_dir, setting_filename)
        with open(settings_path, 'w') as \
                settings_file:
            xml_text = self._settings_template.substitute(dict(parameters + \
                self._fixed_parameters.items()))
            settings_file.write(xml_text)
        output = 'Something went wrong.'
        failure = False
        try:
            output = subprocess.check_output([self._application_path, settings_path], 
                                             cwd=temp_dir,
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = e.output
            failure = True
        finally:
            with open(os.path.join(temp_dir, self._orderer.getStdoutFilename()), 'w') as output_file:
                output_file.write(output)

        destination = self._orderer.orderFiles(iteration, parameters, temp_dir)
        try:
            os.rmdir(temp_dir)
        except OSError as e:
            print 'WARNING: Cannot delete temporary folder:\''+e.filename+'\''
        return iteration, parameters, destination, failure

    def execute(self, processes=None):
        """Execute automation using n processes.

    Args:
        processes: Number of separate processes to run
    """
    
        settings = self._read_settings()
        self._validateTemplateAndParameters(settings)
        self._settings_template = Template(settings)
        comb_count = sum(1 for _ in self._combinations(self._parameters))
        self._orderer.init(self._settings_path, self._output_path, comb_count)
        pool = ThreadPool(processes=processes)
        pool_iterator = pool.imap_unordered(self._run, 
                                            enumerate(self._combinations(self._parameters)))
        print "Xautomate starts... There are %i parameter combinations." % comb_count
        done = 0
        fails = 0
        stats = ''
        with open(os.path.join(self._output_path, 'stats.txt'), 'w') as stats:
            stats.write(repr(tuple(p.name for p in self._parameters))+'\n')
            print 'Done: {:d}/{:d} ({:.0%}) Fails: {:d}'.format(done, comb_count,
                done/float(comb_count), fails),
            for result in pool_iterator:
                done += 1
                if result[3]:
                    fails += 1
                status = 'OK' if not result[3] else 'FAIL'
                relative_path = os.path.relpath(result[2], self._output_path)
                stats.write(repr((self._orderer.getIterationPrefix(result[0]), status, relative_path,
                    tuple(value for _, value in result[1]))) + '\n')
                print '\rDone: {:d}/{:d} ({:.0%}) Fails: {:d}'.format(done, comb_count,
                    done/float(comb_count), fails),
                sys.stdout.flush()
            print
        self._orderer.clean()


class Parameter(object):
    def __init__(self, name):
        self.name = name

    def __iter__(self):
        return self

    def next(self):
        raise StopIteration


class LinearParameter(Parameter):
    def __init__(self, name, start, stop, step):
        super(LinearParameter, self).__init__(name)
        self._start, self._stop, self._step = Decimal(start), Decimal(stop), Decimal(step)
        if self._step == 0:
            sys.exit('Terminated. Parameter \'' + self.name + '\'. Step value is 0.')

    def __iter__(self):
        value = self._start
        while (value >= self._start and value <= self._stop) or \
                (value <= self._start and value >= self._stop):
            yield str(value)
            value += self._step
              

class ProgressionParameter(Parameter):
    def __init__(self, name, base, ratio, u_range):
        super(ProgressionParameter, self).__init__(name)
        self._base, self._ratio, self._u_range = Decimal(base), Decimal(ratio), u_range
        if self._base == 0 or self._ratio == 0:
            sys.exit('Terminated. Parameter \'' + self.name + '\'. Some arguments are wrong.')

    def __iter__(self):
        for i in self._u_range:
            yield str(self._base * (self._ratio ** i))


class ExponentialParameter(Parameter):
    def __init__(self, name, base, u_range):
        super(ExponentialParameter, self).__init__(name)
        self._base, self._u_range = Decimal(base), u_range
        if self._base == 0:
            sys.exit('Terminated. Parameter \'' + self.name + '\'. Some arguments are wrong.')

    def __iter__(self):
        for i in self._u_range:
            yield str(self._base ** i)


class ListParameter(Parameter):
    def __init__(self, name, values):
        super(ListParameter, self).__init__(name)
        self._values = values

    def __iter__(self):
        return self._values.__iter__()


class StringNumberParameter(Parameter):
    def __init__(self, name, length, u_range):
        super(StringNumberParameter, self).__init__(name)
        self._length, self._u_range = length, u_range

    def __iter__(self):
        for value in self._u_range:
            yield '{{:0{:d}d}}'.format(self._length).format(value)


class Orderer(object):
    def init(self, settings_path, output_path, count):
        self._len = len(str(count))
        self._output_path = output_path
        self._settings_ext = os.path.splitext(settings_path)[1]
        try:
            self._root_temp = tempfile.mkdtemp(dir=self._output_path)
        except Exception as e:
            raise e

    def getIterationPrefix(self, iteration):
        return '{{:0{:d}d}}'.format(self._len).format(iteration)

    def getStdoutFilename(self):
        return 'stdout.txt'

    def getSettingFilename(self):
        return  'settings' + self._settings_ext

    def orderFiles(self, parameters, path):
        pass

    def getLocalTempFolder(self):
        try:
            return tempfile.mkdtemp(dir=self._root_temp)
        except Exception as e:
            raise e          

    def clean(self):
        try:
            os.rmdir(self._root_temp)
        except OSError as e:
            print 'WARNING: Cannot delete temporary folder:\''+e.filename+'\''

    def _validateFilename(self, filename, length = 32):
        valid_chars = '-_. %s%s' % (string.ascii_letters, string.digits)
        valid_name = ''.join(c for c in filename if c in valid_chars)
        if len(valid_name) <= length:
            return valid_name
        return valid_name[:length]    


class TreeOrderer(Orderer):
    def __init__(self, depth=0):
        self._depth = depth
        self._lock = threading.Lock()

    def orderFiles(self, iteration, parameters, path):
        parametric_path = [param + '-' + str(value) for param, value in parameters]
        if self._depth == None:
            destination = self._output_path
        else:
            if self._depth <= 0:
                self._depth = len(parametric_path)
            destination = os.path.join(self._output_path, *map(self._validateFilename, 
                                                           parametric_path[:self._depth]))
        with self._lock:
            if not os.path.exists(destination):
                try:
                    os.makedirs(destination)
                except OSError as e:
                    raise e
        for filename in os.listdir(path):
            indexed_filename = '{{:0{:d}d}}_{{:s}}'.format(self._len).format(iteration, filename)
            while True:
                try:
                    os.rename(os.path.join(path, filename), os.path.join(destination, indexed_filename))
                    break
                except Exception, e:
                    if os.path.isfile(os.path.join(destination, indexed_filename)):
                        raise e
        return destination