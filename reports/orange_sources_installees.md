# Sources Orange installées consultées

Orange (API Python), version 3.40.0. Sources locales archivées pour rendre les réglages auditables.

## widgets/data/owdatasampler.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
import math

from AnyQt.QtWidgets import QFormLayout
from AnyQt.QtCore import Qt

import numpy as np
import sklearn.model_selection as skl

from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.data import Table
from Orange.data.sql.table import SqlTable
from Orange.widgets.utils.localization import pl
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Msg, OWWidget, Input, Output
from Orange.util import Reprable


class OWDataSampler(OWWidget):
    name = _tr.m[573, "Data Sampler"]
    description = (_tr.m[574, "Randomly draw a subset of data points "] + _tr.m[575, "from the input dataset."])
    icon = "icons/DataSampler.svg"
    priority = 100
    category = _tr.m[576, "Transform"]
    keywords = _tr.m[577, "data sampler, random"]

    _MAX_SAMPLE_SIZE = 2 ** 31 - 1

    class Inputs:
        data = Input(_tr.m[578, "Data"], Table)

    class Outputs:
        data_sample = Output(_tr.m[579, "Data Sample"], Table, default=True)
        remaining_data = Output(_tr.m[580, "Remaining Data"], Table)

    want_main_area = False
    resizing_enabled = False

    RandomSeed = 42
    FixedProportion, FixedSize, CrossValidation, Bootstrap = range(4)
    SqlTime, SqlProportion = range(2)

    selectedFold: int

    use_seed = Setting(True)
    replacement = Setting(False)
    stratify = Setting(False)
    sql_dl = Setting(False)
    sampling_type = Setting(FixedProportion)
    sampleSizeNumber = Setting(1)
    sampleSizePercentage = Setting(70)
    sampleSizeSqlTime = Setting(1)
    sampleSizeSqlPercentage = Setting(0.1)
    number_of_folds = Setting(10)
    selectedFold = Setting(1)

    # Older versions of the widget had swapped outputs for cross validation
    # Migrations set this to True for compability with older workflows
    compatibility_mode = Setting(False, schema_only=True)

    settings_version = 2

    class Information(OWWidget.Information):
        compatibility_mode = Msg(
            (_tr.m[581, "Compatibility mode\n"] + _tr.m[582, "New versions of widget have swapped outputs for cross validation"])
        )

    class Warning(OWWidget.Warning):
        could_not_stratify = Msg(_tr.m[583, "Stratification failed.\n{}"])
        bigger_sample = Msg(_tr.m[584, 'Sample is bigger than input.'])

    class Error(OWWidget.Error):
        too_many_folds = Msg(_tr.m[585, "Number of subsets exceeds data size."])
        sample_larger_than_data = Msg(_tr.m[586, "Sample can't be larger than data."])
        not_enough_to_stratify = Msg(_tr.m[587, "Data is too small to stratify."])
        no_data = Msg(_tr.m[588, "Dataset is empty."])

    def __init__(self):
        super().__init__()
        if self.compatibility_mode:
            self.Information.compatibility_mode()

        self.data = None
        self.indices = None
        self.sampled_instances = self.remaining_instances = None

        self.sampling_box = gui.vBox(self.controlArea, _tr.m[589, "Sampling Type"])
        sampling = gui.radioButtons(self.sampling_box, self, "sampling_type",
                                    callback=self.sampling_type_changed)

        def set_sampling_type(i):
            def set_sampling_type_i():
                self.sampling_type = i
                self.sampling_type_changed()
            return set_sampling_type_i

        gui.appendRadioButton(sampling, _tr.m[590, "Fixed proportion of data:"])
        self.sampleSizePercentageSlider = gui.hSlider(
            gui.indentedBox(sampling), self,
            "sampleSizePercentage",
            minValue=0, maxValue=100, ticks=10, labelFormat="%d %%",
            callback=set_sampling_type(self.FixedProportion))

        gui.appendRadioButton(sampling, _tr.m[591, "Fixed sample size"])
        ibox = gui.indentedBox(sampling)
        self.sampleSizeSpin = gui.spin(
            ibox, self, "sampleSizeNumber", label=_tr.m[592, "Instances: "],
            minv=0, maxv=self._MAX_SAMPLE_SIZE,
            callback=set_sampling_type(self.FixedSize),
            controlWidth=90)
        gui.checkBox(
            ibox, self, "replacement", _tr.m[593, "Sample with replacement"],
            callback=set_sampling_type(self.FixedSize))

        gui.appendRadioButton(sampling, _tr.m[594, "Cross validation"])
        form = QFormLayout(
            formAlignment=Qt.AlignLeft | Qt.AlignTop,
            labelAlignment=Qt.AlignLeft,
            fieldGrowthPolicy=QFormLayout.AllNonFixedFieldsGrow)
        ibox = gui.indentedBox(sampling, orientation=form)
        form.addRow(_tr.m[595, "Number of subsets:"],
                    gui.spin(
                        ibox, self, "number_of_folds", 2, 100,
                        addToLayout=False,
                        callback=self.number_of_folds_changed))
        self.selected_fold_spin = gui.spin(
            ibox, self, "selectedFold", 1, self.number_of_folds,
            addToLayout=False, callback=self.fold_changed)
        form.addRow(_tr.m[596, "Unused subset:"] if not self.compatibility_mode
                    else _tr.m[597, "Selected subset:"], self.selected_fold_spin)

        gui.appendRadioButton(sampling, _tr.m[598, "Bootstrap"])

        self.sql_box = gui.vBox(self.controlArea, _tr.m[599, "Sampling Type"])
        sampling = gui.radioButtons(self.sql_box, self, "sampling_type",
                                    callback=self.sampling_type_changed)
        gui.appendRadioButton(sampling, _tr.m[600, "Time:"])
        ibox = gui.indentedBox(sampling)
        spin = gui.spin(ibox, self, "sampleSizeSqlTime", minv=1, maxv=3600,
                        callback=set_sampling_type(self.SqlTime))
        spin.setSuffix(_tr.m[601, " sec"])
        gui.appendRadioButton(sampling, _tr.m[602, "Percentage"])
        ibox = gui.indentedBox(sampling)
        spin = gui.spin(ibox, self, "sampleSizeSqlPercentage", spinType=float,
                        minv=0.0001, maxv=100, step=0.1, decimals=4,
                        callback=set_sampling_type(self.SqlProportion))
        spin.setSuffix(" %")
        self.sql_box.setVisible(False)

        self.options_box = gui.vBox(self.controlArea, _tr.m[603, "Options"], addSpaceBefore=False)
        self.cb_seed = gui.checkBox(
            self.options_box, self, "use_seed",
            _tr.m[604, "Replicable (deterministic) sampling"],
            callback=self.settings_changed)
        self.cb_stratify = gui.checkBox(
            self.options_box, self, "stratify",
            _tr.m[605, "Stratify sample (when possible)"], callback=self.settings_changed)
        self.cb_sql_dl = gui.checkBox(
            self.options_box, self, "sql_dl", _tr.m[606, "Download data to local memory"],
            callback=self.settings_changed)
        self.cb_sql_dl.setVisible(False)

        gui.button(self.buttonsArea, self, _tr.m[607, "Sample Data"],
                   callback=self.commit)

    def sampling_type_changed(self):
        self.settings_changed()

    def number_of_folds_changed(self):
        self.selected_fold_spin.setMaximum(self.number_of_folds)
        self.sampling_type = self.CrossValidation
        self.settings_changed()

    def fold_changed(self):
        # a separate callback - if we decide to cache indices
        self.sampling_type = self.CrossValidation

    def settings_changed(self):
        self._update_sample_max_size()
        self.indices = None

    @Inputs.data
    def set_data(self, dataset):
        self.data = dataset
        if dataset is not None:
            sql = isinstance(dataset, SqlTable)
            self.sampling_box.setVisible(not sql)
            self.sql_box.setVisible(sql)
            self.cb_seed.setVisible(not sql)
            self.cb_stratify.setVisible(not sql)
            self.cb_sql_dl.setVisible(sql)

            if not sql:
                self._update_sample_max_size()
                self.updateindices()
        else:
            self.indices = None
            self.clear_messages()
        self.commit()

    def _update_sample_max_size(self):
        """Limit number of instances to input size unless using replacement."""
        if not self.data or self.replacement:
            self.sampleSizeSpin.setMaximum(self._MAX_SAMPLE_SIZE)
        else:
            self.sampleSizeSpin.setMaximum(len(self.data))

    def commit(self):
        if self.data is None:
            sample = other = None
            self.sampled_instances = self.remaining_instances = None
        elif isinstance(self.data, SqlTable):
            other = None
            if self.sampling_type == self.SqlProportion:
                sample = self.data.sample_percentage(
                    self.sampleSizeSqlPercentage, no_cache=True)
            else:
                sample = self.data.sample_time(
                    self.sampleSizeSqlTime, no_cache=True)
            if self.sql_dl:
                sample.download_data()
                sample = Table(sample)

        else:
            if self.indices is None or not self.use_seed:
                self.updateindices()
                if self.indices is None:
                    return
            if self.sampling_type in (
                    self.FixedProportion, self.FixedSize, self.Bootstrap):
                remaining, sample = self.indices
            elif self.sampling_type == self.CrossValidation:
                if self.compatibility_mode:
                    remaining, sample = self.indices[self.selectedFold - 1]
                else:
                    sample, remaining = self.indices[self.selectedFold - 1]

            sample = self.data[sample]
            other = self.data[remaining]
            self.sampled_instances = len(sample)
            self.remaining_instances = len(other)

        self.Outputs.data_sample.send(sample)
        self.Outputs.remaining_data.send(other)

    def updateindices(self):
        self.Error.clear()
        self.Warning.clear()
        repl = True
        data_length = len(self.data)
        num_classes = len(self.data.domain.class_var.values) \
            if self.data.domain.has_discrete_class else 0

        size = None
        if not data_length:
            self.Error.no_data()
        elif self.sampling_type == self.FixedSize:
            size = self.sampleSizeNumber
            repl = self.replacement
        elif self.sampling_type == self.FixedProportion:
            size = np.ceil(self.sampleSizePercentage / 100 * data_length)
            repl = False
        elif self.sampling_type == self.CrossValidation:
            if data_length < self.number_of_folds:
                self.Error.too_many_folds()
        else:
            assert self.sampling_type == self.Bootstrap

        if not repl and size is not None and (size > data_length):
            self.Error.sample_larger_than_data()
        if not repl and data_length <= num_classes and self.stratify:
            self.Error.not_enough_to_stratify()

        if self.Error.active:
            self.indices = None
            return

        # By the above, we can safely assume there is data
        if self.sampling_type == self.FixedSize and repl and size and \
                size > len(self.data):
            # This should only be possible when using replacement
            self.Warning.bigger_sample()

        stratified = (self.stratify and
                      isinstance(self.data, Table) and
                      self.data.domain.has_discrete_class)
        try:
            self.indices = self.sample(data_length, size, stratified)
        except ValueError as ex:
            self.Warning.could_not_stratify(str(ex))
            self.indices = self.sample(data_length, size, stratified=False)

    def sample(self, data_length, size, stratified):
        rnd = self.RandomSeed if self.use_seed else None
        if self.sampling_type == self.FixedSize:
            sampler = SampleRandomN(
                size, stratified=stratified, replace=self.replacement,
                random_state=rnd)
        elif self.sampling_type == self.FixedProportion:
            sampler = SampleRandomP(
                self.sampleSizePercentage / 100, stratified=stratified,
                random_state=rnd)
        elif self.sampling_type == self.Bootstrap:
            sampler = SampleBootstrap(data_length, random_state=rnd)
        else:
            sampler = SampleFoldIndices(
                self.number_of_folds, stratified=stratified, random_state=rnd)
        return sampler(self.data)

    def send_report(self):
        if self.sampling_type == self.FixedProportion:
            tpe = _tr.e(_tr.c(608, f"Random sample with {self.sampleSizePercentage} % of data"))
        elif self.sampling_type == self.FixedSize:
            if self.sampleSizeNumber == 1:
                tpe = _tr.m[609, "Random data instance"]
            else:
                tpe = _tr.e(_tr.c(610, f"Random sample with {self.sampleSizeNumber} data instances"))
                if self.replacement:
                    tpe += _tr.m[611, ", with replacement"]
        elif self.sampling_type == self.CrossValidation:
            tpe = (_tr.e(_tr.c(612, f"{self.number_of_folds}-fold cross-validation ")) + _tr.e(_tr.c(613, f"without subset #{self.selectedFold}")))
        elif self.sampling_type == self.Bootstrap:
            tpe = _tr.m[614, "Bootstrap"]
        else:  # pragma: no cover
            assert False
        if self.stratify:
            tpe += _tr.m[615, ", stratified (if possible)"]
        if self.use_seed:
            tpe += _tr.m[616, ", deterministic"]
        items = [(_tr.m[617, "Sampling type"], tpe)]
        if self.sampled_instances is not None:
            items += [
                (_tr.m[618, "Input"], _tr.e(_tr.c(619, f"{len(self.data)} {pl(len(self.data), 'instance')}"))),
                (_tr.m[620, "Sample"], _tr.e(_tr.c(621, f"{self.sampled_instances} {pl(self.sampled_instances, 'instance')}"))),
                (_tr.m[622, "Remaining"], _tr.e(_tr.c(623, f"{self.remaining_instances} {pl(self.remaining_instances, 'instance')}"))),
            ]
        self.report_items(items)

    @classmethod
    def migrate_settings(cls, settings, version):
        if not version or version < 2 \
                and settings["sampling_type"] == cls.CrossValidation:
            settings["compatibility_mode"] = True


class SampleFoldIndices(Reprable):
    def __init__(self, folds=10, stratified=False, random_state=None):
        """Samples data based on a number of folds.

        Args:
            folds (int): Number of folds
            stratified (bool): Return stratified indices (if applicable).
            random_state (Random): An initial state for replicable random
            behavior

        Returns:
            tuple-of-arrays: A tuple of array indices one for each fold.

        """
        self.folds = folds
        self.stratified = stratified
        self.random_state = random_state

    def __call__(self, table):
        if self.stratified and table.domain.has_discrete_class:
            splitter = skl.StratifiedKFold(
                self.folds, shuffle=True, random_state=self.random_state)
            splitter.get_n_splits(table.X, table.Y)
            ind = splitter.split(table.X, table.Y)
        else:
            splitter = skl.KFold(
                self.folds, shuffle=True, random_state=self.random_state)
            splitter.get_n_splits(table)
            ind = splitter.split(table)
        return tuple(ind)


class SampleRandomN(Reprable):
    def __init__(self, n=0, stratified=False, replace=False,
                 random_state=None):
        self.n = n
        self.stratified = stratified
        self.replace = replace
        self.random_state = random_state

    def __call__(self, table):
        if self.replace:
            # pylint: disable=no-member
            rgen = np.random.RandomState(self.random_state)
            sample = rgen.randint(0, len(table), self.n)
            o = np.ones(len(table))
            o[sample] = 0
            others = np.nonzero(o)[0]
            return others, sample
        if self.n in (0, len(table)):
            rgen = np.random.RandomState(self.random_state)
            shuffled = np.arange(len(table))
            rgen.shuffle(shuffled)
            empty = np.array([], dtype=int)
            if self.n == 0:
                return shuffled, empty
            else:
                return empty, shuffled
        elif self.stratified and table.domain.has_discrete_class:
            test_size = max(len(table.domain.class_var.values), self.n)
            splitter = skl.StratifiedShuffleSplit(
                n_splits=1, test_size=test_size,
                train_size=len(table) - test_size,
                random_state=self.random_state)
            splitter.get_n_splits(table.X, table.Y)
            ind = splitter.split(table.X, table.Y)
        else:
            splitter = skl.ShuffleSplit(
                n_splits=1, test_size=self.n, random_state=self.random_state)
            splitter.get_n_splits(table)
            ind = splitter.split(table)
        return next(iter(ind))


class SampleRandomP(Reprable):
    def __init__(self, p=0, stratified=False, random_state=None):
        self.p = p
        self.stratified = stratified
        self.random_state = random_state

    def __call__(self, table):
        n = int(math.ceil(len(table) * self.p))
        return SampleRandomN(n, self.stratified,
                             random_state=self.random_state)(table)


class SampleBootstrap(Reprable):
    def __init__(self, size=0, random_state=None):
        self.size = size
        self.random_state = random_state

    def __call__(self, table=None):
        """Bootstrap indices

        Args:
            table: Not used (but part of the signature)
        Returns:
            tuple (out_of_sample, sample) indices
        """
        # pylint: disable=no-member
        rgen = np.random.RandomState(self.random_state)
        sample = rgen.randint(0, self.size, self.size)
        sample.sort()  # not needed for the code below, just for the user
        insample = np.ones((self.size,), dtype=bool)
        insample[sample] = False
        remaining = np.flatnonzero(insample)
        return remaining, sample


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWDataSampler).run(Table("iris"))

```

## widgets/evaluate/owtestandscore.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
# pylint doesn't understand the Settings magic
# pylint: disable=invalid-sequence-index
# pylint: disable=too-many-lines,too-many-instance-attributes
import abc
import enum
import logging
import traceback
import copy
from functools import partial, reduce

from concurrent.futures import Future
from collections import OrderedDict
from itertools import count
from typing import (
    Any, Optional, List, Dict, Callable, Sequence, NamedTuple, Tuple
)

import numpy as np
import baycomp

from AnyQt import QtGui
from AnyQt.QtCore import Qt, QSize, QThread
from AnyQt.QtCore import pyqtSlot as Slot
from AnyQt.QtGui import QStandardItem, QDoubleValidator
from AnyQt.QtWidgets import \
    QHeaderView, QTableWidget, QLabel, QComboBox, QSizePolicy

from Orange.base import Learner
import Orange.classification
from Orange.data import Table, DiscreteVariable
from Orange.data.table import DomainTransformationError
from Orange.data.filter import HasClass
from Orange.data.sql.table import SqlTable, AUTO_DL_LIMIT
import Orange.evaluation
from Orange.evaluation import Results
from Orange.preprocess.preprocess import Preprocess
import Orange.regression
from Orange.statistics.util import unique
from Orange.widgets import gui, settings, widget
from Orange.widgets.evaluate.utils import \
    usable_scorers, ScoreTable, learner_name, scorer_caller
from Orange.widgets.utils.itemmodels import DomainModel
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.utils.concurrent import ThreadExecutor, TaskState
from Orange.widgets.widget import OWWidget, Msg, Input, MultiInput, Output

log = logging.getLogger(__name__)


class InputLearner(NamedTuple):
    learner:  Orange.base.Learner
    results: Optional['Try[Orange.evaluation.Results]']
    stats: Optional[Sequence['Try[float]']]
    key: Any


class Try(abc.ABC):
    """Try to walk in a Turing tar pit."""

    class Success:
        """Data type for instance constructed on success"""
        __slots__ = ("__value",)
#         __bool__ = lambda self: True
        success = property(lambda self: True)
        value = property(lambda self: self.__value)

        def __init__(self, value):
            self.__value = value

        def __getnewargs__(self):
            return (self.value,)

        def __repr__(self):
            return "{}({!r})".format(self.__class__.__qualname__,
                                     self.value)

        def map(self, fn):
            return Try(lambda: fn(self.value))

    class Fail:
        """Data type for instance constructed on fail"""
        __slots__ = ("__exception", )
#         __bool__ = lambda self: False
        success = property(lambda self: False)
        exception = property(lambda self: self.__exception)

        def __init__(self, exception):
            self.__exception = exception

        def __getnewargs__(self):
            return (self.exception, )

        def __repr__(self):
            return "{}({!r})".format(self.__class__.__qualname__,
                                     self.exception)

        def map(self, _fn):
            return self

    def __new__(cls, f, *args, **kwargs):
        try:
            rval = f(*args, **kwargs)
        except BaseException as ex:
            # IMPORANT: Will capture traceback in ex.__traceback__
            return Try.Fail(ex)
        else:
            return Try.Success(rval)

Try.register(Try.Success)
Try.register(Try.Fail)


def raise_(exc):
    raise exc

Try.register = lambda cls: raise_(TypeError())


class State(enum.Enum):
    """
    OWTestAndScore's runtime state.
    """
    #: No or insufficient input (i.e. no data or no learners)
    Waiting = "Waiting"
    #: Executing/running the evaluations
    Running = "Running"
    #: Finished running evaluations (success or error)
    Done = "Done"
    #: Evaluation cancelled
    Cancelled = "Cancelled"


class OWTestAndScore(OWWidget):
    name = _tr.m[2077, "Test and Score"]
    description = _tr.m[2078, "Cross-validation accuracy estimation."]
    icon = "icons/TestLearners1.svg"
    priority = 100
    keywords = _tr.m[2079, "test and score, cross validation, cv"]
    replaces = ["Orange.widgets.evaluate.owtestlearners.OWTestLearners"]

    class Inputs:
        train_data = Input(_tr.m[2080, "Data"], Table, default=True)
        test_data = Input(_tr.m[2081, "Test Data"], Table)
        learner = MultiInput(
            _tr.m[2082, "Learner"], Learner, filter_none=True
        )
        preprocessor = Input(_tr.m[2083, "Preprocessor"], Preprocess)

    class Outputs:
        predictions = Output(_tr.m[2084, "Predictions"], Table)
        evaluations_results = Output(_tr.m[2085, "Evaluation Results"], Results)

    settings_version = 4
    buttons_area_orientation = None

    settingsHandler = settings.PerfectDomainContextHandler()
    score_table = settings.SettingProvider(ScoreTable)

    #: Resampling/testing types
    KFold, FeatureFold, ShuffleSplit, LeaveOneOut, TestOnTrain, TestOnTest \
        = 0, 1, 2, 3, 4, 5
    #: Numbers of folds
    NFolds = [2, 3, 5, 10, 20]
    #: Number of repetitions
    NRepeats = [2, 3, 5, 10, 20, 50, 100]
    #: Sample sizes
    SampleSizes = [5, 10, 20, 25, 30, 33, 40, 50, 60, 66, 70, 75, 80, 90, 95]

    #: Selected resampling type
    resampling = settings.Setting(0)
    #: Number of folds for K-fold cross validation
    n_folds = settings.Setting(2)
    #: Stratified sampling for K-fold
    cv_stratified = settings.Setting(True)
    #: Number of repeats for ShuffleSplit sampling
    n_repeats = settings.Setting(3)
    #: ShuffleSplit sample size
    sample_size = settings.Setting(9)
    #: Stratified sampling for Random Sampling
    shuffle_stratified = settings.Setting(True)
    # CV where nr. of feature values determines nr. of folds
    fold_feature = settings.ContextSetting(None)
    fold_feature_selected = settings.ContextSetting(False)

    use_rope = settings.Setting(False)
    rope = settings.Setting(0.1)
    comparison_criterion = settings.Setting(0, schema_only=True)

    TARGET_AVERAGE = _tr.m[2086, "(None, show average over classes)"]
    class_selection = settings.ContextSetting(TARGET_AVERAGE)

    class Error(OWWidget.Error):
        test_data_empty = Msg(_tr.m[2087, "Test dataset is empty."])
        class_required_test = Msg(_tr.m[2088, "Test data input requires a target variable."])
        too_many_folds = Msg(_tr.m[2089, "Number of folds exceeds the data size"])
        class_inconsistent = Msg((_tr.m[2090, "Test and train datasets "] + _tr.m[2091, "have different target variables."]))
        memory_error = Msg(_tr.m[2092, "Not enough memory."])
        test_data_incompatible = Msg(
            _tr.m[2093, "Test data may be incompatible with train data."])
        train_data_error = Msg("{}")

    class Warning(OWWidget.Warning):
        missing_data = \
            Msg(_tr.m[2094, "Instances with unknown target values were removed from{}data."])
        test_data_missing = Msg(_tr.m[2095, "Missing separate test data input."])
        scores_not_computed = Msg(_tr.m[2096, "Some scores could not be computed."])
        test_data_unused = Msg((_tr.m[2097, "Test data is present but unused. "] + _tr.m[2098, "Select 'Test on test data' to use it."]))
        cant_stratify = \
            Msg((_tr.m[2099, "Can't run stratified {}-fold cross validation; "] + _tr.m[2100, "the least common class has only {} instances."]))

    class Information(OWWidget.Information):
        data_sampled = Msg(_tr.m[2101, "Train data has been sampled"])
        test_data_sampled = Msg(_tr.m[2102, "Test data has been sampled"])
        test_data_transformed = Msg(
            _tr.m[2103, "Test data has been transformed to match the train data."])
        cant_stratify_numeric = Msg(_tr.m[2104, "Stratification is ignored for regression"])
        cant_stratify_multitarget = Msg((_tr.m[2105, "Stratification is ignored when there are"] + _tr.m[2106, " multiple target variables."]))

    def __init__(self):
        super().__init__()

        self.data = None
        self.test_data = None
        self.preprocessor = None
        self.train_data_missing_vals = False
        self.test_data_missing_vals = False
        self.scorers = []
        self.__pending_comparison_criterion = self.comparison_criterion
        self.__id_gen = count()
        self._learner_inputs = []  # type: List[Tuple[Any, Learner]]
        #: An Ordered dictionary with current inputs and their testing results
        #: (keyed by ids generated by __id_gen).
        self.learners = OrderedDict()  # type: Dict[Any, Input]

        self.__state = State.Waiting
        # Do we need to [re]test any learners, set by _invalidate and
        # cleared by __update
        self.__needupdate = False
        self.__task = None  # type: Optional[TaskState]
        self.__executor = ThreadExecutor()

        sbox = gui.vBox(self.controlArea, box=True)
        rbox = gui.radioButtons(
            sbox, self, "resampling", callback=self._param_changed)

        gui.appendRadioButton(rbox, _tr.m[2107, "Cross validation"])
        ibox = gui.indentedBox(rbox)
        gui.comboBox(
            ibox, self, "n_folds", label=_tr.m[2108, "Number of folds: "],
            items=[str(x) for x in self.NFolds],
            orientation=Qt.Horizontal, callback=self.kfold_changed)
        gui.checkBox(
            ibox, self, "cv_stratified", _tr.m[2109, "Stratified"],
            callback=self.kfold_changed)
        gui.appendRadioButton(rbox, _tr.m[2110, "Cross validation by feature"])
        ibox = gui.indentedBox(rbox)
        self.feature_model = DomainModel(
            order=DomainModel.METAS, valid_types=DiscreteVariable)
        self.features_combo = gui.comboBox(
            ibox, self, "fold_feature", model=self.feature_model,
            orientation=Qt.Horizontal, searchable=True,
            callback=self.fold_feature_changed)

        gui.appendRadioButton(rbox, _tr.m[2111, "Random sampling"])
        ibox = gui.indentedBox(rbox)
        gui.comboBox(
            ibox, self, "n_repeats", label=_tr.m[2112, "Repeat train/test: "],
            items=[str(x) for x in self.NRepeats], orientation=Qt.Horizontal,
            callback=self.shuffle_split_changed
        )
        gui.comboBox(
            ibox, self, "sample_size", label=_tr.m[2113, "Training set size: "],
            items=["{} %".format(x) for x in self.SampleSizes],
            orientation=Qt.Horizontal, callback=self.shuffle_split_changed
        )
        gui.checkBox(
            ibox, self, "shuffle_stratified", _tr.m[2114, "Stratified"],
            callback=self.shuffle_split_changed)

        gui.appendRadioButton(rbox, _tr.m[2115, "Leave one out"])

        gui.appendRadioButton(rbox, _tr.m[2116, "Test on train data"])
        gui.appendRadioButton(rbox, _tr.m[2117, "Test on test data"])

        gui.rubber(self.controlArea)

        self.score_table = ScoreTable(self)
        self.score_table.shownScoresChanged.connect(self.update_stats_model)
        view = self.score_table.view
        view.setSizeAdjustPolicy(view.AdjustToContents)

        self.results_box = gui.vBox(self.mainArea, box=True)
        self.cbox = gui.hBox(self.results_box)
        self.class_selection_combo = gui.comboBox(
            self.cbox, self, "class_selection", items=[],
            label=_tr.m[2118, "Evaluation results for target"], orientation=Qt.Horizontal,
            sendSelectedValue=True, searchable=True, contentsLength=25,
            callback=self._on_target_class_changed
        )
        self.cbox.layout().addStretch(100)
        self.class_selection_combo.setMaximumContentsLength(30)
        self.results_box.layout().addWidget(self.score_table.view)

        gui.separator(self.mainArea, 16)
        self.compbox = box = gui.vBox(self.mainArea, box=True)
        cbox = gui.comboBox(
            box, self, "comparison_criterion", label=_tr.m[2119, "Compare models by:"],
            sizeAdjustPolicy=QComboBox.AdjustToMinimumContentsLengthWithIcon,
            sizePolicy=(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed),
            orientation=Qt.Horizontal, callback=self.update_comparison_table).box

        gui.separator(cbox, 8)
        gui.checkBox(cbox, self, "use_rope", _tr.m[2120, "Negligible diff.: "],
                     callback=self._on_use_rope_changed)
        gui.lineEdit(cbox, self, "rope", validator=QDoubleValidator(),
                     controlWidth=50, callback=self.update_comparison_table,
                     alignment=Qt.AlignRight)
        self.controls.rope.setEnabled(self.use_rope)

        table = self.comparison_table = QTableWidget(
            wordWrap=False, editTriggers=QTableWidget.NoEditTriggers,
            selectionMode=QTableWidget.NoSelection)
        table.setSizeAdjustPolicy(table.AdjustToContents)
        header = table.verticalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.setSectionsClickable(False)

        header = table.horizontalHeader()
        header.setTextElideMode(Qt.ElideRight)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionsClickable(False)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        avg_width = self.fontMetrics().averageCharWidth()
        header.setMinimumSectionSize(8 * avg_width)
        header.setMaximumSectionSize(15 * avg_width)
        header.setDefaultSectionSize(15 * avg_width)
        box.layout().addWidget(table)
        box.layout().addWidget(QLabel(
            (_tr.m[2121, "<small>Table shows probabilities that the score for the model in "] + (_tr.m[2122, "the row is higher than that of the model in the column. "] + (_tr.m[2123, "Small numbers show the probability that the difference is "] + _tr.m[2124, "negligible.</small>"]))), wordWrap=True))

    def sizeHint(self):
        sh = super().sizeHint()
        return QSize(780, sh.height())

    def _update_controls(self):
        self.fold_feature = None
        self.feature_model.set_domain(None)
        if self.data:
            self.feature_model.set_domain(self.data.domain)
            if self.fold_feature is None and self.feature_model:
                self.fold_feature = self.feature_model[0]
        enabled = bool(self.feature_model)
        self.controls.resampling.buttons[
            OWTestAndScore.FeatureFold].setEnabled(enabled)
        self.features_combo.setEnabled(enabled)
        if self.resampling == OWTestAndScore.FeatureFold and not enabled:
            self.resampling = OWTestAndScore.KFold

    @Inputs.learner
    def set_learner(self, index: int, learner: Learner):
        """
        Set the input `learner` at `index`.

        Parameters
        ----------
        index: int
        learner: Orange.base.Learner
        """
        key, _ = self._learner_inputs[index]
        slot = self.learners[key]
        self.learners[key] = slot._replace(learner=learner, results=None)
        self._invalidate([key])

    @Inputs.learner.insert
    def insert_learner(self, index: int, learner: Learner):
        key = next(self.__id_gen)
        self._learner_inputs.insert(index, (key, learner))
        self.learners[key] = InputLearner(learner, None, None, key)
        self.learners = {key: self.learners[key] for key, _ in self._learner_inputs}
        self._invalidate([key])

    @Inputs.learner.remove
    def remove_learner(self, index: int):
        key, _ = self._learner_inputs[index]
        self._invalidate([key])
        self._learner_inputs.pop(index)
        self.learners.pop(key)

    @Inputs.train_data
    def set_train_data(self, data):
        """
        Set the input training dataset.

        Parameters
        ----------
        data : Optional[Orange.data.Table]
        """
        self.cancel()
        self.Information.data_sampled.clear()
        self.Error.train_data_error.clear()

        if data is not None:
            data_errors = [
                (_tr.m[2125, "Train dataset is empty."], len(data) == 0),
                (
                    _tr.m[2126, "Train data input requires a target variable."],
                    not data.domain.class_vars
                ),
                (_tr.m[2127, "Target variable has no values."], np.isnan(data.Y).all()),
                (
                    _tr.m[2128, "Target variable has only one value."],
                    data.domain.has_discrete_class and len(unique(data.Y)) < 2
                ),
                (_tr.m[2129, "Data has no features to learn from."], data.X.shape[1] == 0),
            ]

            for error_msg, cond in data_errors:
                if cond:
                    self.Error.train_data_error(error_msg)
                    data = None
                    break

        if isinstance(data, SqlTable):
            if data.approx_len() < AUTO_DL_LIMIT:
                data = Table(data)
            else:
                self.Information.data_sampled()
                data_sample = data.sample_time(1, no_cache=True)
                data_sample.download_data(AUTO_DL_LIMIT, partial=True)
                data = Table(data_sample)

        self.train_data_missing_vals = \
            data is not None and np.isnan(data.Y).any()
        if self.train_data_missing_vals or self.test_data_missing_vals:
            self.Warning.missing_data(self._which_missing_data())
            if data:
                data = HasClass()(data)
        else:
            self.Warning.missing_data.clear()

        self.data = data
        self.closeContext()
        self._update_scorers()
        self._update_controls()
        if data is not None:
            self._update_class_selection()
            self.openContext(data.domain)
            if self.fold_feature_selected and bool(self.feature_model):
                self.resampling = OWTestAndScore.FeatureFold
        self._invalidate()

    @Inputs.test_data
    def set_test_data(self, data):
        # type: (Orange.data.Table) -> None
        """
        Set the input separate testing dataset.

        Parameters
        ----------
        data : Optional[Orange.data.Table]
        """
        self.Information.test_data_sampled.clear()
        self.Error.test_data_empty.clear()
        if data is not None and not data:
            self.Error.test_data_empty()
            data = None

        if data and not data.domain.class_vars:
            self.Error.class_required_test()
            data = None
        else:
            self.Error.class_required_test.clear()

        if isinstance(data, SqlTable):
            if data.approx_len() < AUTO_DL_LIMIT:
                data = Table(data)
            else:
                self.Information.test_data_sampled()
                data_sample = data.sample_time(1, no_cache=True)
                data_sample.download_data(AUTO_DL_LIMIT, partial=True)
                data = Table(data_sample)

        self.test_data_missing_vals = \
            data is not None and np.isnan(data.Y).any()
        if self.train_data_missing_vals or self.test_data_missing_vals:
            self.Warning.missing_data(self._which_missing_data())
            if data:
                data = HasClass()(data)
        else:
            self.Warning.missing_data.clear()

        self.test_data = data
        if self.resampling == OWTestAndScore.TestOnTest:
            self._invalidate()

    def _which_missing_data(self):
        return {(True, True): " ",  # both, don't specify
                (True, False): _tr.m[2130, " train "],
                (False, True): _tr.m[2131, " test "]}[(self.train_data_missing_vals,
                                          self.test_data_missing_vals)]

    # List of scorers shouldn't be retrieved globally, when the module is
    # loading since add-ons could have registered additional scorers.
    # It could have been cached but
    # - we don't gain much with it
    # - it complicates the unit tests
    def _update_scorers(self):
        new_scorers = []
        if self.data:
            new_scorers = usable_scorers(self.data.domain)

        # Don't unnecessarily reset the combo because this would always reset
        # comparison_criterion; we also set it explicitly, though, for clarity
        if new_scorers != self.scorers:
            self.scorers = new_scorers
            combo = self.controls.comparison_criterion
            combo.clear()
            combo.addItems([scorer.long_name or scorer.name
                            for scorer in self.scorers])
            if self.scorers:
                self.comparison_criterion = 0
        if self.__pending_comparison_criterion is not None:
            # Check for the unlikely case that some scorers have been removed
            # from modules
            if self.__pending_comparison_criterion < len(self.scorers):
                self.comparison_criterion = self.__pending_comparison_criterion
            self.__pending_comparison_criterion = None

    @Inputs.preprocessor
    def set_preprocessor(self, preproc):
        """
        Set the input preprocessor to apply on the training data.
        """
        self.preprocessor = preproc
        self._invalidate()

    def handleNewSignals(self):
        """Reimplemented from OWWidget.handleNewSignals."""
        self._update_class_selection()
        self.score_table.update_header(self.scorers)
        self._update_view_enabled()
        self.update_stats_model()
        if self.__needupdate:
            self.__update()

    def kfold_changed(self):
        self.resampling = OWTestAndScore.KFold
        self._param_changed()

    def fold_feature_changed(self):
        self.resampling = OWTestAndScore.FeatureFold
        self._param_changed()

    def shuffle_split_changed(self):
        self.resampling = OWTestAndScore.ShuffleSplit
        self._param_changed()

    def _param_changed(self):
        self._update_view_enabled()
        self._invalidate()
        self.__update()

    def _update_view_enabled(self):
        self.compbox.setEnabled(
            self.resampling == OWTestAndScore.KFold
            and len(self.learners) > 1
            and self.data is not None)
        self.score_table.view.setEnabled(
            self.data is not None)

    def update_stats_model(self):
        # Update the results_model with up to date scores.
        # Note: The target class specific scores (if requested) are
        # computed as needed in this method.
        model = self.score_table.model
        # clear the table model, but preserving the header labels
        for r in reversed(range(model.rowCount())):
            model.takeRow(r)

        target_index = None
        if self.data is not None:
            class_var = self.data.domain.class_var
            if self.data.domain.has_discrete_class and \
                            self.class_selection != self.TARGET_AVERAGE:
                target_index = class_var.values.index(self.class_selection)
        else:
            class_var = None

        errors = []
        has_missing_scores = False

        names = []
        for key, slot in self.learners.items():
            name = learner_name(slot.learner)
            names.append(name)
            head = QStandardItem(name)
            head.setData(key, Qt.UserRole)
            results = slot.results
            if results is not None and results.success:
                train = QStandardItem("{:.3f}".format(results.value.train_time))
                train.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                train.setData(key, Qt.UserRole)
                test = QStandardItem("{:.3f}".format(results.value.test_time))
                test.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                test.setData(key, Qt.UserRole)
                row = [head, train, test]
            else:
                row = [head]
            if isinstance(results, Try.Fail):
                head.setToolTip(str(results.exception))
                head.setText(_tr.m[2132, "{} (error)"].format(name))
                head.setForeground(QtGui.QBrush(Qt.red))
                if isinstance(results.exception, DomainTransformationError) \
                        and self.resampling == self.TestOnTest:
                    self.Error.test_data_incompatible()
                    self.Information.test_data_transformed.clear()
                else:
                    errors.append((_tr.m[2133, "{name} failed with error:\n"] + "{exc.__class__.__name__}: {exc!s}")
                                  .format(name=name, exc=slot.results.exception)
                                  )

            if class_var is not None and class_var.is_discrete and \
                    target_index is not None:
                if slot.results is not None and slot.results.success:
                    ovr_results = results_one_vs_rest(
                        slot.results.value, target_index)

                    # Cell variable is used immediatelly, it's not stored
                    # pylint: disable=cell-var-from-loop
                    stats = [Try(scorer_caller(scorer, ovr_results, target=1))
                             for scorer in self.scorers]
                else:
                    stats = None
            else:
                stats = slot.stats

            if stats is not None:
                for stat, scorer in zip(stats, self.scorers):
                    item = QStandardItem()
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if stat.success:
                        item.setData(float(stat.value[0]), Qt.DisplayRole)
                    else:
                        item.setToolTip(str(stat.exception))
                        # pylint: disable=unsubscriptable-object
                        if self.score_table.show_score_hints[scorer.__name__]:
                            has_missing_scores = True
                    row.append(item)

            model.appendRow(row)

        # Resort rows based on current sorting
        header = self.score_table.view.horizontalHeader()
        model.sort(
            header.sortIndicatorSection(),
            header.sortIndicatorOrder()
        )
        self._set_comparison_headers(names)

        self.error("\n".join(errors), shown=bool(errors))
        self.Warning.scores_not_computed(shown=has_missing_scores)

    def _on_use_rope_changed(self):
        self.controls.rope.setEnabled(self.use_rope)
        self.update_comparison_table()

    def update_comparison_table(self):
        self.comparison_table.clearContents()
        slots = self._successful_slots()
        if not (slots and self.scorers):
            return
        names = [learner_name(slot.learner) for slot in slots]
        self._set_comparison_headers(names)
        if self.resampling == OWTestAndScore.KFold:
            scores = self._scores_by_folds(slots)
            self._fill_table(names, scores)

    def _successful_slots(self):
        model = self.score_table.model
        proxy = self.score_table.sorted_model

        keys = (model.data(proxy.mapToSource(proxy.index(row, 0)), Qt.UserRole)
                for row in range(proxy.rowCount()))
        slots = [slot for slot in (self.learners[key] for key in keys)
                 if slot.results is not None and slot.results.success]
        return slots

    def _set_comparison_headers(self, names):
        table = self.comparison_table
        try:
            # Prevent glitching during update
            table.setUpdatesEnabled(False)
            header = table.horizontalHeader()
            if len(names) > 2:
                header.setSectionResizeMode(QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(QHeaderView.Fixed)
            table.setRowCount(len(names))
            table.setColumnCount(len(names))
            table.setVerticalHeaderLabels(names)
            table.setHorizontalHeaderLabels(names)
        finally:
            table.setUpdatesEnabled(True)

    def _scores_by_folds(self, slots):
        scorer = self.scorers[self.comparison_criterion]()
        if scorer.is_binary:
            if self.class_selection != self.TARGET_AVERAGE:
                class_var = self.data.domain.class_var
                target_index = class_var.values.index(self.class_selection)
                kw = dict(target=target_index)
            else:
                kw = dict(average='weighted')
        else:
            kw = {}

        def call_scorer(results):
            def thunked():
                return scorer.scores_by_folds(results.value, **kw).flatten()

            return thunked

        scores = [Try(call_scorer(slot.results)) for slot in slots]
        scores = [score.value if score.success else None for score in scores]
        # `None in scores doesn't work -- these are np.arrays)
        if any(score is None for score in scores):
            self.Warning.scores_not_computed()
        return scores

    def _fill_table(self, names, scores):
        table = self.comparison_table
        for row, row_name, row_scores in zip(count(), names, scores):
            for col, col_name, col_scores in zip(range(row), names, scores):
                if row_scores is None or col_scores is None:
                    continue
                if self.use_rope and self.rope:
                    p0, rope, p1 = baycomp.two_on_single(
                        row_scores, col_scores, self.rope)
                    if np.isnan(p0) or np.isnan(rope) or np.isnan(p1):
                        self._set_cells_na(table, row, col)
                        continue
                    self._set_cell(table, row, col,
                                   f"{p0:.3f}<br/><small>{rope:.3f}</small>",
                                   (f"p({row_name} > {col_name}) = {p0:.3f}\n" + f"p({row_name} = {col_name}) = {rope:.3f}"))
                    self._set_cell(table, col, row,
                                   f"{p1:.3f}<br/><small>{rope:.3f}</small>",
                                   (f"p({col_name} > {row_name}) = {p1:.3f}\n" + f"p({col_name} = {row_name}) = {rope:.3f}"))
                else:
                    p0, p1 = baycomp.two_on_single(row_scores, col_scores)
                    if np.isnan(p0) or np.isnan(p1):
                        self._set_cells_na(table, row, col)
                        continue
                    self._set_cell(table, row, col,
                                   f"{p0:.3f}",
                                   f"p({row_name} > {col_name}) = {p0:.3f}")
                    self._set_cell(table, col, row,
                                   f"{p1:.3f}",
                                   f"p({col_name} > {row_name}) = {p1:.3f}")

    @classmethod
    def _set_cells_na(cls, table, row, col):
        cls._set_cell(table, row, col, "NA", "comparison cannot be computed")
        cls._set_cell(table, col, row, "NA", "comparison cannot be computed")

    @staticmethod
    def _set_cell(table, row, col, label, tooltip):
        item = QLabel(label)
        item.setToolTip(tooltip)
        item.setAlignment(Qt.AlignCenter)
        table.setCellWidget(row, col, item)

    def _update_class_selection(self):
        self.class_selection_combo.setCurrentIndex(-1)
        self.class_selection_combo.clear()
        if not self.data:
            return

        if self.data.domain.has_discrete_class:
            self.cbox.setVisible(True)
            class_var = self.data.domain.class_var
            items = (self.TARGET_AVERAGE, ) + class_var.values
            self.class_selection_combo.addItems(items)

            class_index = 0
            if self.class_selection in class_var.values:
                class_index = class_var.values.index(self.class_selection) + 1

            self.class_selection_combo.setCurrentIndex(class_index)
            self.class_selection = items[class_index]
        else:
            self.cbox.setVisible(False)

    def _on_target_class_changed(self):
        self.update_stats_model()
        self.update_comparison_table()

    def _invalidate(self, which=None):
        self.cancel()
        self.fold_feature_selected = \
            self.resampling == OWTestAndScore.FeatureFold
        # Invalidate learner results for `which` input keys
        # (if None then all learner results are invalidated)
        if which is None:
            which = self.learners.keys()

        model = self.score_table.model
        statmodelkeys = [model.item(row, 0).data(Qt.UserRole)
                         for row in range(model.rowCount())]

        for key in which:
            self.learners[key] = \
                self.learners[key]._replace(results=None, stats=None)

            if key in statmodelkeys:
                row = statmodelkeys.index(key)
                for c in range(1, model.columnCount()):
                    item = model.item(row, c)
                    if item is not None:
                        item.setData(None, Qt.DisplayRole)
                        item.setData(None, Qt.ToolTipRole)

        self.comparison_table.clearContents()

        self.__needupdate = True

    def commit(self):
        """
        Commit the results to output.
        """
        self.Error.memory_error.clear()
        valid = [slot for slot in self.learners.values()
                 if slot.results is not None and slot.results.success]
        combined = None
        predictions = None
        if valid:
            # Evaluation results
            combined = results_merge([slot.results.value for slot in valid])
            combined.learner_names = [learner_name(slot.learner)
                                      for slot in valid]

            # Predictions & Probabilities
            try:
                predictions = combined.get_augmented_data(combined.learner_names)
            except MemoryError:
                self.Error.memory_error()

        self.Outputs.evaluations_results.send(combined)
        self.Outputs.predictions.send(predictions)

    def send_report(self):
        """Report on the testing schema and results"""
        if not self.data or not self.learners:
            return
        if self.resampling == self.KFold:
            stratified = _tr.m[2134, 'Stratified '] if self.cv_stratified else ''
            items = [(_tr.m[2135, "Sampling type"], _tr.m[2136, "{}{}-fold Cross validation"].
                      format(stratified, self.NFolds[self.n_folds]))]
        elif self.resampling == self.LeaveOneOut:
            items = [(_tr.m[2137, "Sampling type"], _tr.m[2138, "Leave one out"])]
        elif self.resampling == self.ShuffleSplit:
            stratified = _tr.m[2139, 'Stratified '] if self.shuffle_stratified else ''
            items = [(_tr.m[2140, "Sampling type"],
                      _tr.m[2141, "{}Shuffle split, {} random samples with {}% data "]
                      .format(stratified, self.NRepeats[self.n_repeats],
                              self.SampleSizes[self.sample_size]))]
        elif self.resampling == self.TestOnTrain:
            items = [(_tr.m[2142, "Sampling type"], _tr.m[2143, "No sampling, test on training data"])]
        elif self.resampling == self.TestOnTest:
            items = [(_tr.m[2144, "Sampling type"], _tr.m[2145, "No sampling, test on testing data"])]
        else:
            items = []
        if self.data.domain.has_discrete_class:
            items += [(_tr.m[2146, "Target class"], self.class_selection.strip("()"))]
        if items:
            self.report_items(_tr.m[2147, "Settings"], items)
        self.report_table(_tr.m[2148, "Scores"], self.score_table.view)

    @classmethod
    def migrate_settings(cls, settings_, version):
        if version < 2:
            if settings_["resampling"] > 0:
                settings_["resampling"] += 1
        if version < 3:
            # Older version used an incompatible context handler
            settings_["context_settings"] = [
                c for c in settings_.get("context_settings", ())
                if not hasattr(c, 'classes')]
        if version < 4:
            if "score_table" in settings_:
                ScoreTable.migrate_to_show_scores_hints(settings_["score_table"])

    @Slot(float)
    def setProgressValue(self, value):
        self.progressBarSet(value)

    def __update(self):
        self.__needupdate = False

        assert self.__task is None or self.__state == State.Running
        if self.__state == State.Running:
            self.cancel()

        self.Warning.test_data_unused.clear()
        self.Error.test_data_incompatible.clear()
        self.Warning.test_data_missing.clear()
        self.Warning.cant_stratify.clear()
        self.Information.cant_stratify_numeric.clear()
        self.Information.cant_stratify_multitarget.clear()
        self.Information.test_data_transformed(
            shown=self.resampling == self.TestOnTest
            and self.data is not None
            and self.test_data is not None
            and self.data.domain.attributes != self.test_data.domain.attributes)
        self.warning()
        self.Error.class_inconsistent.clear()
        self.Error.too_many_folds.clear()
        self.error()

        # check preconditions and return early or show warnings
        if self.data is None:
            self.__state = State.Waiting
            self.commit()
            return
        if not self.learners:
            self.__state = State.Waiting
            self.commit()
            return
        if self.resampling == OWTestAndScore.KFold:
            k = self.NFolds[self.n_folds]
            if len(self.data) < k:
                self.Error.too_many_folds()
                self.__state = State.Waiting
                self.commit()
                return
            do_stratify = self.cv_stratified
            if do_stratify:
                if len(self.data.domain.class_vars) > 1:
                    self.Information.cant_stratify_multitarget()
                    do_stratify = False
                elif self.data.domain.class_var.is_discrete:
                    least = min(filter(None,
                                       np.bincount(self.data.Y.astype(int))))
                    if least < k:
                        self.Warning.cant_stratify(k, least)
                        do_stratify = False
                else:
                    self.Information.cant_stratify_numeric()
                    do_stratify = False

        elif self.resampling == OWTestAndScore.TestOnTest:
            if self.test_data is None:
                if not self.Error.test_data_empty.is_shown():
                    self.Warning.test_data_missing()
                self.__state = State.Waiting
                self.commit()
                return
            elif self.test_data.domain.class_var != self.data.domain.class_var:
                self.Error.class_inconsistent()
                self.__state = State.Waiting
                self.commit()
                return

        elif self.test_data is not None:
            self.Warning.test_data_unused()

        rstate = 42
        # items in need of an update
        items = [(key, slot) for key, slot in self.learners.items()
                 if slot.results is None]
        learners = [slot.learner for _, slot in items]

        # deepcopy all learners as they are not thread safe (by virtue of
        # the base API). These will be the effective learner objects tested
        # but will be replaced with the originals on return (see restore
        # learners bellow)
        learners_c = [copy.deepcopy(learner) for learner in learners]

        if self.resampling == OWTestAndScore.TestOnTest:
            test_f = partial(
                Orange.evaluation.TestOnTestData(
                    store_data=True, store_models=True),
                self.data, self.test_data, learners_c, self.preprocessor
            )
        else:
            if self.resampling == OWTestAndScore.KFold:
                sampler = Orange.evaluation.CrossValidation(
                    k=self.NFolds[self.n_folds],
                    random_state=rstate,
                    stratified=do_stratify)
            elif self.resampling == OWTestAndScore.FeatureFold:
                sampler = Orange.evaluation.CrossValidationFeature(
                    feature=self.fold_feature)
            elif self.resampling == OWTestAndScore.LeaveOneOut:
                sampler = Orange.evaluation.LeaveOneOut()
            elif self.resampling == OWTestAndScore.ShuffleSplit:
                sampler = Orange.evaluation.ShuffleSplit(
                    n_resamples=self.NRepeats[self.n_repeats],
                    train_size=self.SampleSizes[self.sample_size] / 100,
                    test_size=None,
                    stratified=self.shuffle_stratified,
                    random_state=rstate)
            elif self.resampling == OWTestAndScore.TestOnTrain:
                sampler = Orange.evaluation.TestOnTrainingData(
                    store_models=True)
            else:
                assert False, "self.resampling %s" % self.resampling

            sampler.store_data = True
            test_f = partial(
                sampler, self.data, learners_c, self.preprocessor)

        def replace_learners(evalfunc, *args, **kwargs):
            res = evalfunc(*args, **kwargs)
            assert all(lc is lo for lc, lo in zip(learners_c, res.learners))
            res.learners[:] = learners
            return res

        test_f = partial(replace_learners, test_f)

        self.__submit(test_f)

    def __submit(self, testfunc):
        # type: (Callable[[Callable[[float], None]], Results]) -> None
        """
        Submit a testing function for evaluation

        MUST not be called if an evaluation is already pending/running.
        Cancel the existing task first.

        Parameters
        ----------
        testfunc : Callable[[Callable[float]], Results])
            Must be a callable taking a single `callback` argument and
            returning a Results instance
        """
        assert self.__state != State.Running
        # Setup the task
        task = TaskState()

        def progress_callback(finished):
            if task.is_interruption_requested():
                raise UserInterrupt()
            task.set_progress_value(100 * finished)

        testfunc = partial(testfunc, callback=progress_callback)
        task.start(self.__executor, testfunc)

        task.progress_changed.connect(self.setProgressValue)
        task.watcher.finished.connect(self.__task_complete)

        self.Outputs.evaluations_results.invalidate()
        self.Outputs.predictions.invalidate()
        self.progressBarInit()
        self.setStatusMessage(_tr.m[2149, "Running"])

        self.__state = State.Running
        self.__task = task

    @Slot(object)
    def __task_complete(self, f: 'Future[Results]'):
        # handle a completed task
        assert self.thread() is QThread.currentThread()
        assert self.__task is not None and self.__task.future is f
        self.progressBarFinished()
        self.setStatusMessage("")
        assert f.done()
        self.__task = None
        self.__state = State.Done
        try:
            results = f.result()    # type: Results
            learners = results.learners  # type: List[Learner]
        except Exception as er:  # pylint: disable=broad-except
            log.exception("testing error (in __task_complete):",
                          exc_info=True)
            self.error("\n".join(traceback.format_exception_only(type(er), er)))
            return

        learner_key = {slot.learner: key for key, slot in
                       self.learners.items()}
        assert all(learner in learner_key for learner in learners)

        # Update the results for individual learners
        for learner, result in zip(learners, results.split_by_model()):
            ex = result.failed[0]
            if ex:
                stats = [Try.Fail(ex)] * len(self.scorers)
                result = Try.Fail(ex)
            else:
                stats = [Try(scorer_caller(scorer, result))
                         for scorer in self.scorers]
                result = Try.Success(result)
            key = learner_key.get(learner)
            self.learners[key] = \
                self.learners[key]._replace(results=result, stats=stats)

        self.score_table.update_header(self.scorers)
        self.update_stats_model()
        self.update_comparison_table()

        self.commit()

    def cancel(self):
        """
        Cancel the current/pending evaluation (if any).
        """
        if self.__task is not None:
            assert self.__state == State.Running
            self.__state = State.Cancelled
            task, self.__task = self.__task, None
            task.cancel()
            task.progress_changed.disconnect(self.setProgressValue)
            task.watcher.finished.disconnect(self.__task_complete)

            self.progressBarFinished()
            self.setStatusMessage("")

    def onDeleteWidget(self):
        self.cancel()
        self.__executor.shutdown(wait=False)
        super().onDeleteWidget()

    def copy_to_clipboard(self):
        self.score_table.copy_selection_to_clipboard()


class UserInterrupt(BaseException):
    """
    A BaseException subclass used for cooperative task/thread cancellation
    """


def results_add_by_model(x, y):
    def is_empty(res):
        return (getattr(res, "models", None) is None
                and getattr(res, "row_indices", None) is None)

    if is_empty(x):
        return y
    elif is_empty(y):
        return x

    assert (x.row_indices == y.row_indices).all()
    assert (x.actual == y.actual).all()

    res = Orange.evaluation.Results()
    res.data = x.data
    res.domain = x.domain
    res.row_indices = x.row_indices
    res.folds = x.folds
    res.actual = x.actual
    res.predicted = np.vstack((x.predicted, y.predicted))
    if getattr(x, "probabilities", None) is not None \
            and getattr(y, "probabilities") is not None:
        res.probabilities = np.vstack((x.probabilities, y.probabilities))

    if x.models is not None:
        res.models = np.hstack((x.models, y.models))
    return res


def results_merge(results):
    return reduce(results_add_by_model, results, Orange.evaluation.Results())


def results_one_vs_rest(results, pos_index):
    from Orange.preprocess.transformation import Indicator
    actual = results.actual == pos_index
    predicted = results.predicted == pos_index
    if results.probabilities is not None:
        c = results.probabilities.shape[2]
        assert c >= 2
        neg_indices = [i for i in range(c) if i != pos_index]
        pos_prob = results.probabilities[:, :, [pos_index]]
        neg_prob = np.sum(results.probabilities[:, :, neg_indices],
                          axis=2, keepdims=True)
        probabilities = np.dstack((neg_prob, pos_prob))
    else:
        probabilities = None

    res = Orange.evaluation.Results()
    res.actual = actual
    res.predicted = predicted
    res.folds = results.folds
    res.row_indices = results.row_indices
    res.probabilities = probabilities

    value = results.domain.class_var.values[pos_index]
    class_var = Orange.data.DiscreteVariable(
        "I({}=={})".format(results.domain.class_var.name, value),
        values=("False", "True"),
        compute_value=Indicator(results.domain.class_var, pos_index)
    )
    domain = Orange.data.Domain(
        results.domain.attributes,
        [class_var],
        results.domain.metas
    )
    res.data = None
    res.domain = domain
    return res


if __name__ == "__main__":  # pragma: no cover
    filename = "iris"
    preview_data = Table(filename)
    if preview_data.domain.class_var.is_discrete:
        prev_learners = [lambda data: 1 / 0,
                         Orange.classification.LogisticRegressionLearner(),
                         Orange.classification.MajorityLearner(),
                         Orange.classification.NaiveBayesLearner()]
    else:
        prev_learners = [lambda data: 1 / 0,
                         Orange.regression.MeanLearner(),
                         Orange.regression.KNNRegressionLearner(),
                         Orange.regression.RidgeRegressionLearner()]

    WidgetPreview(OWTestAndScore).run(
        set_train_data=preview_data,
        set_test_data=preview_data,
        insert_learner=list(enumerate(prev_learners))
    )

```

## widgets/model/owsavemodel.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
import pickle

from Orange.widgets.widget import Input
from Orange.base import Model
from Orange.widgets.utils.save.owsavebase import OWSaveBase
from Orange.widgets.utils.widgetpreview import WidgetPreview


class OWSaveModel(OWSaveBase):
    name = _tr.m[2473, "Save Model"]
    description = _tr.m[2474, "Save a trained model to an output file."]
    icon = "icons/SaveModel.svg"
    replaces = ["Orange.widgets.classify.owsaveclassifier.OWSaveClassifier"]
    priority = 3000
    keywords = _tr.m[2475, "save model, save"]

    class Inputs:
        model = Input("Model", Model)

    filters = [_tr.m[2476, "Pickled model (*.pkcls)"]]

    @Inputs.model
    def set_model(self, model):
        self.data = model
        self.on_new_input()

    def do_save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.data, f)


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWSaveModel).run()

```

## widgets/model/owlogisticregression.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from itertools import chain
import numpy as np
from AnyQt.QtCore import Qt

from orangewidget.report import bool_str

from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.classification.logistic_regression import LogisticRegressionLearner
from Orange.widgets import settings, gui
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.signals import Output
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Msg


class OWLogisticRegression(OWBaseLearner):
    name = _tr.m[2314, "Logistic Regression"]
    description = (_tr.m[2315, "The logistic regression classification algorithm with "] + _tr.m[2316, "LASSO (L1) or ridge (L2) regularization."])
    icon = "icons/LogisticRegression.svg"
    replaces = [
        "Orange.widgets.classify.owlogisticregression.OWLogisticRegression",
    ]
    priority = 60
    keywords = _tr.m[2317, "logistic regression"]

    LEARNER = LogisticRegressionLearner

    class Outputs(OWBaseLearner.Outputs):
        coefficients = Output(_tr.m[2318, "Coefficients"], Table, explicit=True)

    settings_version = 2
    penalty_type = settings.Setting(1)
    C_index = settings.Setting(61)
    class_weight = settings.Setting(False)

    C_s = list(chain(range(1000, 200, -50),
                     range(200, 100, -10),
                     range(100, 20, -5),
                     range(20, 0, -1),
                     [x / 10 for x in range(9, 2, -1)],
                     [x / 100 for x in range(20, 2, -1)],
                     [x / 1000 for x in range(20, 0, -1)]))
    strength_C = C_s[61]
    dual = False
    tol = 0.0001
    fit_intercept = True
    intercept_scaling = 1.0
    max_iter = 10000

    penalty_types = ("Lasso (L1)", "Ridge (L2)", _tr.m[2319, "None"])
    penalty_types_short = ["l1", "l2", None]

    class Warning(OWBaseLearner.Warning):
        class_weights_used = Msg(_tr.m[2320, "Weighting by class may decrease performance."])

    def add_main_layout(self):
        # this is part of init, pylint: disable=attribute-defined-outside-init
        box = gui.widgetBox(self.controlArea, box=True)
        self.penalty_combo = gui.comboBox(
            box, self, "penalty_type", label=_tr.m[2321, "Regularization type: "],
            items=self.penalty_types, orientation=Qt.Horizontal,
            callback=self._penalty_type_changed)
        self.c_box = box = gui.widgetBox(box)
        gui.widgetLabel(box, _tr.m[2322, "Strength:"])
        box2 = gui.hBox(gui.indentedBox(box))
        gui.widgetLabel(box2, _tr.m[2323, "Weak"]).setStyleSheet("margin-top:6px")
        self.c_slider = gui.hSlider(
            box2, self, "C_index", minValue=0, maxValue=len(self.C_s) - 1,
            callback=self.set_c, callback_finished=self.settings_changed,
            createLabel=False)
        gui.widgetLabel(box2, _tr.m[2324, "Strong"]).setStyleSheet("margin-top:6px")
        box2 = gui.hBox(box)
        box2.layout().setAlignment(Qt.AlignCenter)
        self.c_label = gui.widgetLabel(box2)
        self.set_c()

        box = gui.widgetBox(self.controlArea, box=True)
        self.weights = gui.checkBox(
            box, self,
            "class_weight", label=_tr.m[2325, "Balance class distribution"],
            callback=self.settings_changed,
            tooltip=_tr.m[2326, "Weigh classes inversely proportional to their frequencies."]
        )

    def set_c(self):
        self.strength_C = self.C_s[self.C_index]
        penalty = self.penalty_types_short[self.penalty_type]
        enable_c = penalty is not None
        self.c_box.setEnabled(enable_c)
        if enable_c:
            fmt = "C={}" if self.strength_C >= 1 else "C={:.3f}"
            self.c_label.setText(fmt.format(self.strength_C))
        else:
            self.c_label.setText(_tr.m[2327, "N/A"])

    def set_penalty(self, penalty):
        self.penalty_type = self.penalty_types_short.index(penalty)
        self._penalty_type_changed()

    def _penalty_type_changed(self):
        self.set_c()
        self.settings_changed()

    def create_learner(self):
        self.Warning.class_weights_used.clear()
        penalty = self.penalty_types_short[self.penalty_type]
        if self.class_weight:
            class_weight = "balanced"
            self.Warning.class_weights_used()
        else:
            class_weight = None
        if penalty is None:
            C = 1.0
        else:
            C = self.strength_C
        return self.LEARNER(
            penalty=penalty,
            dual=self.dual,
            tol=self.tol,
            C=C,
            class_weight=class_weight,
            fit_intercept=self.fit_intercept,
            intercept_scaling=self.intercept_scaling,
            max_iter=self.max_iter,
            preprocessors=self.preprocessors,
            random_state=0
        )

    def update_model(self):
        super().update_model()
        coef_table = None
        if self.model is not None:
            coef_table = create_coef_table(self.model)
        self.Outputs.coefficients.send(coef_table)

    def get_learner_parameters(self):
        return ((_tr.m[2328, "Regularization"], _tr.m[2329, "{}, C={}, class weights: {}"].format(
            self.penalty_types[self.penalty_type], self.C_s[self.C_index],
            bool_str(self.class_weight))),)


def create_coef_table(classifier):
    i = classifier.intercept
    c = classifier.coefficients
    if c.shape[0] > 2:
        values = [classifier.domain.class_var.values[int(i)] for i in classifier.used_vals[0]]
    else:
        values = [classifier.domain.class_var.values[int(classifier.used_vals[0][1])]]
    domain = Domain([ContinuousVariable(value) for value in values],
                    metas=[StringVariable(_tr.m[2330, "name"])])
    coefs = np.vstack((i.reshape(1, len(i)), c.T))
    names = [[attr.name] for attr in classifier.domain.attributes]
    names = [[_tr.m[2331, "intercept"]]] + names
    names = np.array(names, dtype=object)
    coef_table = Table.from_numpy(domain, X=coefs, metas=names)
    coef_table.name = _tr.m[2332, "coefficients"]
    return coef_table


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWLogisticRegression).run(Table("zoo"))

```

## widgets/model/owknn.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from AnyQt.QtCore import Qt

from Orange.data import Table
from Orange.modelling import KNNLearner
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview


class OWKNNLearner(OWBaseLearner):
    name = _tr.m[2266, "kNN"]
    description = _tr.m[2267, "Predict according to the nearest training instances."]
    icon = "icons/KNN.svg"
    replaces = [
        "Orange.widgets.classify.owknn.OWKNNLearner",
        "Orange.widgets.regression.owknnregression.OWKNNRegression",
    ]
    priority = 20
    keywords = _tr.m[2268, "knn, k nearest, knearest, neighbor, neighbour"]

    LEARNER = KNNLearner

    weights = ["uniform", "distance"]
    metrics = ["euclidean", "manhattan", "chebyshev", "mahalanobis"]

    weights_options = [_tr.m[2269, "Uniform"], _tr.m[2270, "By Distances"]]
    metrics_options = [_tr.m[2271, "Euclidean"], _tr.m[2272, "Manhattan"], _tr.m[2273, "Chebyshev"], _tr.m[2274, "Mahalanobis"]]

    n_neighbors = Setting(5)
    metric_index = Setting(0)
    weight_index = Setting(0)

    def add_main_layout(self):
        # this is part of init, pylint: disable=attribute-defined-outside-init
        box = gui.vBox(self.controlArea, _tr.m[2275, "Neighbors"])
        self.n_neighbors_spin = gui.spin(
            box, self, "n_neighbors", 1, 100, label=_tr.m[2276, "Number of neighbors:"],
            alignment=Qt.AlignRight, callback=self.settings_changed,
            controlWidth=80)
        self.metrics_combo = gui.comboBox(
            box, self, "metric_index", orientation=Qt.Horizontal,
            label=_tr.m[2277, "Metric:"], items=self.metrics_options,
            callback=self.settings_changed)
        self.weights_combo = gui.comboBox(
            box, self, "weight_index", orientation=Qt.Horizontal,
            label=_tr.m[2278, "Weight:"], items=self.weights_options,
            callback=self.settings_changed)

    def create_learner(self):
        return self.LEARNER(
            n_neighbors=self.n_neighbors,
            metric=self.metrics[self.metric_index],
            weights=self.weights[self.weight_index],
            preprocessors=self.preprocessors)

    def get_learner_parameters(self):
        return ((_tr.m[2279, "Number of neighbours"], self.n_neighbors),
                (_tr.m[2280, "Metric"], self.metrics_options[self.metric_index]),
                (_tr.m[2281, "Weight"], self.weights_options[self.weight_index]))


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWKNNLearner).run(Table("iris"))

```

## widgets/model/owtree.py

```python
"""Tree learner widget"""
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator

from collections import OrderedDict

from AnyQt.QtCore import Qt

from Orange.data import Table
from Orange.modelling.tree import TreeLearner
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.localization import pl
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview


class OWTreeLearner(OWBaseLearner):
    """Tree algorithm with forward pruning."""
    name = _tr.m[2573, "Tree"]
    description = _tr.m[2574, "A tree algorithm with forward pruning."]
    icon = "icons/Tree.svg"
    replaces = [
        "Orange.widgets.classify.owclassificationtree.OWClassificationTree",
        "Orange.widgets.regression.owregressiontree.OWRegressionTree",
        "Orange.widgets.classify.owclassificationtree.OWTreeLearner",
        "Orange.widgets.regression.owregressiontree.OWTreeLearner",
    ]
    priority = 30
    keywords = _tr.m[2575, "tree, classification tree"]

    LEARNER = TreeLearner

    binary_trees = Setting(True)
    limit_min_leaf = Setting(True)
    min_leaf = Setting(2)
    limit_min_internal = Setting(True)
    min_internal = Setting(5)
    limit_depth = Setting(True)
    max_depth = Setting(100)

    # Classification only settings
    limit_majority = Setting(True)
    sufficient_majority = Setting(95)

    spin_boxes = (
        (_tr.m[2576, "Min. number of instances in leaves: "],
         "limit_min_leaf", "min_leaf", 1, 1000),
        (_tr.m[2577, "Do not split subsets smaller than: "],
         "limit_min_internal", "min_internal", 1, 1000),
        (_tr.m[2578, "Limit the maximal tree depth to: "],
         "limit_depth", "max_depth", 1, 1000))

    classification_spin_boxes = (
        (_tr.m[2579, "Stop when majority reaches [%]: "],
         "limit_majority", "sufficient_majority", 51, 100),)

    def add_main_layout(self):
        box = gui.widgetBox(self.controlArea, _tr.m[2580, 'Parameters'])
        # the checkbox is put into vBox for alignemnt with other checkboxes
        gui.checkBox(box, self, "binary_trees", _tr.m[2581, "Induce binary tree"],
                     callback=self.settings_changed,
                     attribute=Qt.WA_LayoutUsesWidgetRect)
        for label, check, setting, fromv, tov in self.spin_boxes:
            gui.spin(box, self, setting, fromv, tov, label=label,
                     checked=check, alignment=Qt.AlignRight,
                     callback=self.settings_changed,
                     checkCallback=self.settings_changed, controlWidth=80)

    def add_classification_layout(self, box):
        for label, check, setting, minv, maxv in self.classification_spin_boxes:
            gui.spin(box, self, setting, minv, maxv,
                     label=label, checked=check, alignment=Qt.AlignRight,
                     callback=self.settings_changed, controlWidth=80,
                     checkCallback=self.settings_changed)

    def learner_kwargs(self):
        # Pylint doesn't get our Settings
        # pylint: disable=invalid-sequence-index
        return dict(
            max_depth=(None, self.max_depth)[self.limit_depth],
            min_samples_split=(2, self.min_internal)[self.limit_min_internal],
            min_samples_leaf=(1, self.min_leaf)[self.limit_min_leaf],
            binarize=self.binary_trees,
            preprocessors=self.preprocessors,
            sufficient_majority=(1, self.sufficient_majority / 100)[
                self.limit_majority])

    def create_learner(self):
        # pylint: disable=not-callable
        return self.LEARNER(**self.learner_kwargs())

    def get_learner_parameters(self):
        from Orange.widgets.report import plural_w
        items = OrderedDict()
        items[_tr.m[2582, "Pruning"]] = ", ".join(s for s, c in (
            ((_tr.e(_tr.c(2583, f'at least {self.min_leaf} ')) + _tr.e(_tr.c(2584, f'{pl(self.min_leaf, "instance")} in leaves'))),
             self.limit_min_leaf),
            ((_tr.e(_tr.c(2585, f'at least {self.min_internal} ')) + _tr.e(_tr.c(2586, f'{pl(self.min_internal, "instance")} in internal nodes'))),
             self.limit_min_internal),
            (_tr.e(_tr.c(2587, f'maximum depth {self.max_depth}')),
             self.limit_depth)
        ) if c) or _tr.m[2588, "None"]
        if self.limit_majority:
            items[_tr.m[2589, "Splitting"]] = (_tr.m[2590, "Stop splitting when majority reaches %d%% "] + _tr.m[2591, "(classification only)"]) % \
                                 self.sufficient_majority
        items[_tr.m[2592, "Binary trees"]] = (_tr.m[2593, "No"], _tr.m[2594, "Yes"])[self.binary_trees]
        return items


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWTreeLearner).run(Table("iris"))

```

## widgets/model/owrandomforest.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from AnyQt.QtCore import Qt

from Orange.data import Table
from Orange.modelling import RandomForestLearner
from Orange.widgets import settings, gui
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Msg


class OWRandomForest(OWBaseLearner):
    name = _tr.m[2386, "Random Forest"]
    description = _tr.m[2387, "Predict using an ensemble of decision trees."]
    icon = "icons/RandomForest.svg"
    replaces = [
        "Orange.widgets.classify.owrandomforest.OWRandomForest",
        "Orange.widgets.regression.owrandomforestregression.OWRandomForestRegression",
    ]
    priority = 40
    keywords = _tr.m[2388, "random forest"]

    LEARNER = RandomForestLearner

    n_estimators = settings.Setting(10)
    max_features = settings.Setting(5)
    use_max_features = settings.Setting(False)
    use_random_state = settings.Setting(False)
    max_depth = settings.Setting(3)
    use_max_depth = settings.Setting(False)
    min_samples_split = settings.Setting(5)
    use_min_samples_split = settings.Setting(True)
    index_output = settings.Setting(0)
    class_weight = settings.Setting(False)

    class Error(OWBaseLearner.Error):
        not_enough_features = Msg(_tr.m[2389, "Insufficient number of attributes ({})"])

    class Warning(OWBaseLearner.Warning):
        class_weights_used = Msg(_tr.m[2390, "Weighting by class may decrease performance."])

    def add_main_layout(self):
        # this is part of init, pylint: disable=attribute-defined-outside-init
        box = gui.vBox(self.controlArea, _tr.m[2391, 'Basic Properties'])
        self.n_estimators_spin = gui.spin(
            box, self, "n_estimators", minv=1, maxv=10000, controlWidth=80,
            alignment=Qt.AlignRight, label=_tr.m[2392, "Number of trees: "],
            callback=self.settings_changed)
        self.max_features_spin = gui.spin(
            box, self, "max_features", 1, 50, controlWidth=80,
            label=_tr.m[2393, "Number of attributes considered at each split: "],
            callback=self.settings_changed, checked="use_max_features",
            checkCallback=self.settings_changed, alignment=Qt.AlignRight,)
        self.random_state = gui.checkBox(
            box, self, "use_random_state", label=_tr.m[2394, "Replicable training"],
            callback=self.settings_changed,
            attribute=Qt.WA_LayoutUsesWidgetRect)
        self.weights = gui.checkBox(
            box, self,
            "class_weight", label=_tr.m[2395, "Balance class distribution"],
            callback=self.settings_changed,
            tooltip=_tr.m[2396, "Weigh classes inversely proportional to their frequencies."],
            attribute=Qt.WA_LayoutUsesWidgetRect
        )

        box = gui.vBox(self.controlArea, _tr.m[2397, "Growth Control"])
        self.max_depth_spin = gui.spin(
            box, self, "max_depth", 1, 50, controlWidth=80,
            label=_tr.m[2398, "Limit depth of individual trees: "], alignment=Qt.AlignRight,
            callback=self.settings_changed, checked="use_max_depth",
            checkCallback=self.settings_changed)
        self.min_samples_split_spin = gui.spin(
            box, self, "min_samples_split", 2, 1000, controlWidth=80,
            label=_tr.m[2399, "Do not split subsets smaller than: "],
            callback=self.settings_changed, checked="use_min_samples_split",
            checkCallback=self.settings_changed, alignment=Qt.AlignRight)

    def create_learner(self):
        self.Warning.class_weights_used.clear()
        common_args = {"n_estimators": self.n_estimators}
        if self.use_max_features:
            common_args["max_features"] = self.max_features
        if self.use_random_state:
            common_args["random_state"] = 0
        if self.use_max_depth:
            common_args["max_depth"] = self.max_depth
        if self.use_min_samples_split:
            common_args["min_samples_split"] = self.min_samples_split
        if self.class_weight:
            common_args["class_weight"] = "balanced"
            self.Warning.class_weights_used()

        return self.LEARNER(preprocessors=self.preprocessors, **common_args)

    def check_data(self):
        self.Error.not_enough_features.clear()
        if super().check_data():
            n_features = len(self.data.domain.attributes)
            if self.use_max_features and self.max_features > n_features:
                self.Error.not_enough_features(n_features)
                self.valid_data = False
        return self.valid_data

    def get_learner_parameters(self):
        """Called by send report to list the parameters of the learner."""
        return (
            (_tr.m[2400, "Number of trees"], self.n_estimators),
            (_tr.m[2401, "Maximal number of considered features"],
             self.max_features if self.use_max_features else _tr.m[2402, "unlimited"]),
            (_tr.m[2403, "Replicable training"], [_tr.m[2404, "No"], _tr.m[2405, "Yes"]][self.use_random_state]),
            (_tr.m[2406, "Maximal tree depth"],
             self.max_depth if self.use_max_depth else _tr.m[2407, "unlimited"]),
            (_tr.m[2408, "Stop splitting nodes with maximum instances"],
             self.min_samples_split if self.use_min_samples_split else
             _tr.m[2409, "unlimited"]),
            (_tr.m[2410, "Class weights"], self.class_weight)
        )


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWRandomForest).run(Table("iris"))

```

## widgets/model/owgradientboosting.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from itertools import chain
from random import randint
from typing import Tuple, Dict, Callable, Type

from AnyQt.QtCore import Qt
from AnyQt.QtGui import QStandardItem, QStandardItemModel
from AnyQt.QtWidgets import QWidget, QVBoxLayout

from Orange.base import Learner
from Orange.data import Table
from Orange.modelling import GBLearner

try:
    from Orange.modelling import CatGBLearner
except ImportError:
    CatGBLearner = None
try:
    from Orange.modelling import XGBLearner, XGBRFLearner
except ImportError:
    XGBLearner = XGBRFLearner = None

from Orange.widgets import gui
from Orange.widgets.settings import Setting, SettingProvider
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview


class LearnerItemModel(QStandardItemModel):
    LEARNERS = [
        (GBLearner, "", ""),
        (XGBLearner, "Extreme Gradient Boosting (xgboost)", "xgboost"),
        (XGBRFLearner, "Extreme Gradient Boosting Random Forest (xgboost)",
         "xgboost"),
        (CatGBLearner, "Gradient Boosting (catboost)", "catboost"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._add_data()

    def _add_data(self):
        for cls, opt_name, lib in self.LEARNERS:
            item = QStandardItem()
            imported = bool(cls)
            name = cls.name if imported else opt_name
            item.setData(f"{name}", Qt.DisplayRole)
            item.setEnabled(imported)
            if not imported:
                item.setToolTip(_tr.e(_tr.c(2232, f"{lib} is not installed")))
            self.appendRow(item)


class BaseEditor(QWidget, gui.OWComponent):
    learner_class: Type[Learner] = NotImplemented
    n_estimators: int = NotImplemented
    learning_rate: float = NotImplemented
    random_state: bool = NotImplemented
    max_depth: int = NotImplemented

    def __init__(self, parent: OWBaseLearner):
        QWidget.__init__(self, parent)
        gui.OWComponent.__init__(self, parent)
        self.settings_changed: Callable = parent.settings_changed

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._layout: QWidget = gui.vBox(self, spacing=6, margin=0)

        self._add_main_layout()

    def _add_main_layout(self):
        common_args = {"callback": self.settings_changed,
                       "alignment": Qt.AlignRight, "controlWidth": 80}
        self.basic_box = gui.vBox(self._layout, _tr.m[2233, "Basic Properties"])
        gui.spin(
            self.basic_box, self, "n_estimators", 1, 10000,
            label=_tr.m[2234, "Number of trees:"], **common_args
        )
        gui.doubleSpin(
            self.basic_box, self, "learning_rate", 0, 1, 0.001,
            label=_tr.m[2235, "Learning rate: "], **common_args
        )
        gui.checkBox(
            self.basic_box, self, "random_state", label=_tr.m[2236, "Replicable training"],
            callback=self.settings_changed, attribute=Qt.WA_LayoutUsesWidgetRect
        )

        self.growth_box = gui.vBox(self._layout, _tr.m[2237, "Growth Control"])
        gui.spin(
            self.growth_box, self, "max_depth", 1, 50,
            label=_tr.m[2238, "Limit depth of individual trees: "], **common_args
        )

        self.sub_box = gui.vBox(self._layout, _tr.m[2239, "Subsampling"])

    def get_arguments(self) -> Dict:
        return {
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "random_state": 0 if self.random_state else randint(1, 1000000),
            "max_depth": self.max_depth,
        }

    def get_learner_parameters(self) -> Tuple:
        return (
            (_tr.m[2240, "Method"], self.learner_class.name),
            (_tr.m[2241, "Number of trees"], self.n_estimators),
            (_tr.m[2242, "Learning rate"], self.learning_rate),
            (_tr.m[2243, "Replicable training"], _tr.m[2244, "Yes"] if self.random_state else _tr.m[2245, "No"]),
            (_tr.m[2246, "Maximum tree depth"], self.max_depth),
        )


class RegEditor(BaseEditor):
    LAMBDAS = list(chain([x / 10000 for x in range(1, 10)],
                         [x / 1000 for x in range(1, 20)],
                         [x / 100 for x in range(2, 20)],
                         [x / 10 for x in range(2, 9)],
                         range(1, 20),
                         range(20, 100, 5),
                         range(100, 1001, 100)))

    lambda_index: int = NotImplemented

    @property
    def lambda_(self):
        return self.LAMBDAS[int(self.lambda_index)]

    def _add_main_layout(self):
        super()._add_main_layout()
        # Basic properties
        box = self.basic_box
        gui.separator(box, height=1)
        gui.widgetLabel(box, _tr.m[2247, "Regularization:"])
        gui.hSlider(
            box, self, "lambda_index", minValue=0, createLabel=False,
            maxValue=len(self.LAMBDAS) - 1, callback=self._set_lambda_label,
            callback_finished=self.settings_changed
        )
        box2 = gui.hBox(box)
        box2.layout().setAlignment(Qt.AlignCenter)
        self.lambda_label = gui.widgetLabel(box2, "")
        self._set_lambda_label()

    def _set_lambda_label(self):
        self.lambda_label.setText("Lambda: {}".format(self.lambda_))

    def get_arguments(self) -> Dict:
        params = super().get_arguments()
        params["reg_lambda"] = self.lambda_
        return params

    def get_learner_parameters(self) -> Tuple:
        return super().get_learner_parameters() + (
            (_tr.m[2248, "Regularization strength"], self.lambda_),
        )


class GBLearnerEditor(BaseEditor):
    learner_class = GBLearner
    n_estimators = Setting(100)
    learning_rate = Setting(0.1)
    random_state = Setting(True)
    subsample = Setting(1)
    max_depth = Setting(3)
    min_samples_split = Setting(2)

    def _add_main_layout(self):
        super()._add_main_layout()
        # Subsampling
        gui.doubleSpin(
            self.sub_box, self, "subsample", 0.05, 1, 0.05,
            controlWidth=80, alignment=Qt.AlignRight,
            label=_tr.m[2249, "Fraction of training instances: "],
            callback=self.settings_changed
        )
        # Growth control
        gui.spin(
            self.growth_box, self, "min_samples_split", 2, 1000,
            controlWidth=80, label=_tr.m[2250, "Do not split subsets smaller than: "],
            alignment=Qt.AlignRight, callback=self.settings_changed
        )

    def get_arguments(self) -> Dict:
        params = super().get_arguments()
        params["subsample"] = self.subsample
        params["min_samples_split"] = self.min_samples_split
        return params

    def get_learner_parameters(self) -> Tuple:
        return super().get_learner_parameters() + (
            (_tr.m[2251, "Fraction of training instances"], self.subsample),
            (_tr.m[2252, "Stop splitting nodes with maximum instances"],
             self.min_samples_split),
        )


class CatGBLearnerEditor(RegEditor):
    learner_class = CatGBLearner
    n_estimators = Setting(100)
    learning_rate = Setting(0.3)
    random_state = Setting(True)
    max_depth = Setting(6)
    lambda_index = Setting(55)  # 3
    colsample_bylevel = Setting(1)

    def _add_main_layout(self):
        super()._add_main_layout()
        # Subsampling
        gui.doubleSpin(
            self.sub_box, self, "colsample_bylevel", 0.05, 1, 0.05,
            controlWidth=80, alignment=Qt.AlignRight,
            label=_tr.m[2253, "Fraction of features for each tree: "],
            callback=self.settings_changed
        )

    def get_arguments(self) -> Dict:
        params = super().get_arguments()
        params["colsample_bylevel"] = self.colsample_bylevel
        return params

    def get_learner_parameters(self) -> Tuple:
        return super().get_learner_parameters() + (
            (_tr.m[2254, "Fraction of features for each tree"], self.colsample_bylevel),
        )


class XGBBaseEditor(RegEditor):
    learner_class = XGBLearner
    n_estimators = Setting(100)
    learning_rate = Setting(0.3)
    random_state = Setting(True)
    max_depth = Setting(6)
    lambda_index = Setting(53)  # 1
    subsample = Setting(1)
    colsample_bytree = Setting(1)
    colsample_bylevel = Setting(1)
    colsample_bynode = Setting(1)

    def _add_main_layout(self):
        super()._add_main_layout()
        # Subsampling
        common_args = {"callback": self.settings_changed,
                       "alignment": Qt.AlignRight, "controlWidth": 80}
        gui.doubleSpin(
            self.sub_box, self, "subsample", 0.05, 1, 0.05,
            label=_tr.m[2255, "Fraction of training instances: "], **common_args
        )
        gui.doubleSpin(
            self.sub_box, self, "colsample_bytree", 0.05, 1, 0.05,
            label=_tr.m[2256, "Fraction of features for each tree: "], **common_args
        )
        gui.doubleSpin(
            self.sub_box, self, "colsample_bylevel", 0.05, 1, 0.05,
            label=_tr.m[2257, "Fraction of features for each level: "], **common_args
        )
        gui.doubleSpin(
            self.sub_box, self, "colsample_bynode", 0.05, 1, 0.05,
            label=_tr.m[2258, "Fraction of features for each split: "], **common_args
        )

    def get_arguments(self) -> Dict:
        params = super().get_arguments()
        params["subsample"] = self.subsample
        params["colsample_bytree"] = self.colsample_bytree
        params["colsample_bylevel"] = self.colsample_bylevel
        params["colsample_bynode"] = self.colsample_bynode
        return params

    def get_learner_parameters(self) -> Tuple:
        return super().get_learner_parameters() + (
            (_tr.m[2259, "Fraction of training instances"], self.subsample),
            (_tr.m[2260, "Fraction of features for each tree"], self.colsample_bytree),
            (_tr.m[2261, "Fraction of features for each level"], self.colsample_bylevel),
            (_tr.m[2262, "Fraction of features for each split"], self.colsample_bynode),
        )


class XGBLearnerEditor(XGBBaseEditor):
    learner_class = XGBLearner


class XGBRFLearnerEditor(XGBBaseEditor):
    learner_class = XGBRFLearner


class OWGradientBoosting(OWBaseLearner):
    name = "Gradient Boosting"
    description = _tr.m[2263, "Predict using gradient boosting on decision trees."]
    icon = "icons/GradientBoosting.svg"
    priority = 45
    keywords = _tr.m[2264, "gradient boosting, catboost, gradient, boost, tree, forest, xgb, gb, extreme"]

    LEARNER: Learner = GBLearner
    editor: BaseEditor = None

    gb_editor = SettingProvider(GBLearnerEditor)
    xgb_editor = SettingProvider(XGBLearnerEditor)
    xgbrf_editor = SettingProvider(XGBRFLearnerEditor)
    catgb_editor = SettingProvider(CatGBLearnerEditor)
    method_index = Setting(0)

    def add_main_layout(self):
        # this is part of init, pylint: disable=attribute-defined-outside-init
        box = gui.vBox(self.controlArea, _tr.m[2265, "Method"])
        gui.comboBox(
            box, self, "method_index", model=LearnerItemModel(self),
            callback=self.__method_changed
        )
        self.gb_editor = GBLearnerEditor(self)
        self.xgb_editor = XGBLearnerEditor(self)
        self.xgbrf_editor = XGBRFLearnerEditor(self)
        self.catgb_editor = CatGBLearnerEditor(self)
        self.editors = [self.gb_editor, self.xgb_editor,
                        self.xgbrf_editor, self.catgb_editor]

        editor_box = gui.widgetBox(self.controlArea)
        for editor in self.editors:
            editor_box.layout().addWidget(editor)
            editor.hide()

        if self.editors[int(self.method_index)].learner_class is None:
            self.method_index = 0
        self.editor = self.editors[int(self.method_index)]
        self.editor.show()

    def __method_changed(self):
        self.editor.hide()
        self.editor = self.editors[int(self.method_index)]
        self.editor.show()
        self.settings_changed()

    def create_learner(self) -> Learner:
        learner = self.editor.learner_class
        kwargs = self.editor.get_arguments()
        return learner(preprocessors=self.preprocessors, **kwargs)

    def get_learner_parameters(self) -> Tuple:
        return self.editor.get_learner_parameters()


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWGradientBoosting).run(Table("iris"))

```

## classification/logistic_regression.py

```python
import numpy as np
import sklearn.linear_model as skl_linear_model

from Orange.classification import SklLearner, SklModel
from Orange.preprocess import Normalize
from Orange.preprocess.score import LearnerScorer
from Orange.data import Variable, DiscreteVariable


__all__ = ["LogisticRegressionLearner"]


class _FeatureScorerMixin(LearnerScorer):
    feature_type = Variable
    class_type = DiscreteVariable

    def score(self, data):
        data = Normalize()(data)
        model = self(data)
        return np.abs(model.coefficients), model.domain.attributes


class LogisticRegressionClassifier(SklModel):
    @property
    def intercept(self):
        return self.skl_model.intercept_

    @property
    def coefficients(self):
        return self.skl_model.coef_


class LogisticRegressionLearner(SklLearner, _FeatureScorerMixin):
    __wraps__ = skl_linear_model.LogisticRegression
    __returns__ = LogisticRegressionClassifier
    preprocessors = SklLearner.preprocessors
    supports_weights = True

    def __init__(self, penalty="l2", dual=False, tol=0.0001, C=1.0,
                 fit_intercept=True, intercept_scaling=1, class_weight=None,
                 random_state=None, solver="auto", max_iter=100,
                 verbose=0, n_jobs=1, preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

    def _initialize_wrapped(self):
        params = self.params.copy()

        # The default scikit-learn solver `lbfgs` (v0.22) does not support the
        # l1 penalty.
        solver, penalty = params.pop("solver"), params.get("penalty")
        if solver == "auto":
            if penalty == "l1":
                solver = "saga"
            else:
                solver = "lbfgs"
        params["solver"] = solver

        return self.__wraps__(**params)


```

## classification/knn.py

```python
import sklearn.neighbors as skl_neighbors
from Orange.base import KNNBase
from Orange.classification import SklLearner

__all__ = ["KNNLearner"]


class KNNLearner(KNNBase, SklLearner):
    __wraps__ = skl_neighbors.KNeighborsClassifier
    supports_weights = False

```

## classification/tree.py

```python
"""Tree inducers: SKL and Orange's own inducer"""
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
import numpy as np
import scipy.sparse as sp
import sklearn.tree as skl_tree

from Orange.base import TreeModel as TreeModelInterface
from Orange.classification import SklLearner, SklModel, Learner
from Orange.classification import _tree_scorers
from Orange.statistics import distribution, contingency
from Orange.tree import Node, DiscreteNode, MappedDiscreteNode, \
    NumericNode, TreeModel

__all__ = ["SklTreeLearner", "TreeLearner"]


class TreeLearner(Learner):
    """
    Tree inducer with proper handling of nominal attributes and binarization.

    The inducer can handle missing values of attributes and target.
    For discrete attributes with more than two possible values, each value can
    get a separate branch (`binarize=False`), or values can be grouped into
    two groups (`binarize=True`, default).

    The tree growth can be limited by the required number of instances for
    internal nodes and for leafs, the sufficient proportion of majority class,
    and by the maximal depth of the tree.

    If the tree is not binary, it can contain zero-branches.

    Args:
        binarize (bool):
            if `True` the inducer will find optimal split into two
            subsets for values of discrete attributes. If `False` (default),
            each value gets its branch.

        min_samples_leaf (float):
            the minimal number of data instances in a leaf

        min_samples_split (float):
            the minimal nubmer of data instances that is
            split into subgroups

        max_depth (int): the maximal depth of the tree

        sufficient_majority (float):
            a majority at which the data is not split
            further

    Returns:
        instance of OrangeTreeModel
    """
    __returns__ = TreeModel

    # Binarization is exhaustive, so we set a limit on the number of values
    MAX_BINARIZATION = 16

    def __init__(
            self, *args, binarize=False, max_depth=None,
            min_samples_leaf=1, min_samples_split=2, sufficient_majority=0.95,
            preprocessors=None, **kwargs):
        super().__init__(preprocessors=preprocessors)
        self.params = {}
        self.binarize = self.params['binarize'] = binarize
        self.min_samples_leaf = self.params['min_samples_leaf'] = min_samples_leaf
        self.min_samples_split = self.params['min_samples_split'] = min_samples_split
        self.sufficient_majority = self.params['sufficient_majority'] = sufficient_majority
        self.max_depth = self.params['max_depth'] = max_depth

    def _select_attr(self, data):
        """Select the attribute for the next split.

        Returns:
            tuple with an instance of Node and a numpy array indicating
            the branch index for each data instance, or -1 if data instance
            is dropped
        """
        # Prevent false warnings by pylint
        attr = attr_no = None
        col_x = None
        REJECT_ATTRIBUTE = 0, None, None, 0

        def _score_disc():
            """Scoring for discrete attributes, no binarization

            The class computes the entropy itself, not by calling other
            functions. This is to make sure that it uses the same
            definition as the below classes that compute entropy themselves
            for efficiency reasons."""
            n_values = len(attr.values)
            if n_values < 2:
                return REJECT_ATTRIBUTE

            cont = _tree_scorers.contingency(col_x, len(data.domain.attributes[attr_no].values),
                                             data.Y, len(data.domain.class_var.values))
            attr_distr = np.sum(cont, axis=0)
            null_nodes = attr_distr < self.min_samples_leaf
            # This is just for speed. If there is only a single non-null-node,
            # entropy wouldn't decrease anyway.
            if sum(null_nodes) >= n_values - 1:
                return REJECT_ATTRIBUTE
            cont[:, null_nodes] = 0
            attr_distr = np.sum(cont, axis=0)
            cls_distr = np.sum(cont, axis=1)
            n = np.sum(attr_distr)
            # Avoid log(0); <= instead of == because we need an array
            cls_distr[cls_distr <= 0] = 1
            attr_distr[attr_distr <= 0] = 1
            cont[cont <= 0] = 1
            class_entr = n * np.log(n) - np.sum(cls_distr * np.log(cls_distr))
            attr_entr = np.sum(attr_distr * np.log(attr_distr))
            cont_entr = np.sum(cont * np.log(cont))
            score = (class_entr - attr_entr + cont_entr) / n / np.log(2)
            score *= n / len(data)  # punishment for missing values
            branches = col_x.copy()
            branches[np.isnan(branches)] = -1
            if score == 0:
                return REJECT_ATTRIBUTE
            node = DiscreteNode(attr, attr_no, None)
            return score, node, branches, n_values

        def _score_disc_bin():
            """Scoring for discrete attributes, with binarization"""
            n_values = len(attr.values)
            if n_values <= 2:
                return _score_disc()
            cont = contingency.Discrete(data, attr)
            attr_distr = np.sum(cont, axis=0)
            # Skip instances with missing value of the attribute
            cls_distr = np.sum(cont, axis=1)
            if np.sum(attr_distr) == 0:  # all values are missing
                return REJECT_ATTRIBUTE
            best_score, best_mapping = _tree_scorers.find_binarization_entropy(
                cont, cls_distr, attr_distr, self.min_samples_leaf)
            if best_score <= 0:
                return REJECT_ATTRIBUTE
            best_score *= 1 - np.sum(cont.unknowns) / len(data)
            mapping, branches = MappedDiscreteNode.branches_from_mapping(
                col_x, best_mapping, n_values)
            node = MappedDiscreteNode(attr, attr_no, mapping, None)
            return best_score, node, branches, 2

        def _score_cont():
            """Scoring for numeric attributes"""
            nans = np.sum(np.isnan(col_x))
            non_nans = len(col_x) - nans
            arginds = np.argsort(col_x)[:non_nans]
            best_score, best_cut = _tree_scorers.find_threshold_entropy(
                col_x, data.Y, arginds,
                len(class_var.values), self.min_samples_leaf)
            if best_score == 0:
                return REJECT_ATTRIBUTE
            best_score *= non_nans / len(col_x)
            branches = np.full(len(col_x), -1, dtype=int)
            mask = ~np.isnan(col_x)
            branches[mask] = (col_x[mask] > best_cut).astype(int)
            node = NumericNode(attr, attr_no, best_cut, None)
            return best_score, node, branches, 2

        #######################################
        # The real _select_attr starts here
        is_sparse = sp.issparse(data.X)
        domain = data.domain
        class_var = domain.class_var
        best_score, *best_res = REJECT_ATTRIBUTE
        best_res = [Node(None, None, None)] + best_res[1:]
        disc_scorer = _score_disc_bin if self.binarize else _score_disc
        for attr_no, attr in enumerate(domain.attributes):
            col_x = data.X[:, attr_no]
            if is_sparse:
                col_x = col_x.toarray()
                col_x = col_x.flatten()
            sc, *res = disc_scorer() if attr.is_discrete else _score_cont()
            if res[0] is not None and sc > best_score:
                best_score, best_res = sc, res
        best_res[0].value = distribution.Discrete(data, class_var)
        return best_res

    def _build_tree(self, data, active_inst, level=1):
        """Induce a tree from the given data

        Returns:
            root node (Node)"""
        node_insts = data[active_inst]
        distr = distribution.Discrete(node_insts, data.domain.class_var)
        if len(node_insts) < self.min_samples_leaf:
            return None
        if len(node_insts) < self.min_samples_split or \
                max(distr) >= sum(distr) * self.sufficient_majority or \
                self.max_depth is not None and level > self.max_depth:
            node, branches, n_children = Node(None, None, distr), None, 0
        else:
            node, branches, n_children = self._select_attr(node_insts)
        node.subset = active_inst
        if branches is not None:
            node.children = [
                self._build_tree(data, active_inst[branches == br], level + 1)
                for br in range(n_children)]
        return node

    def fit_storage(self, data):
        if self.binarize and any(
                attr.is_discrete and len(attr.values) > self.MAX_BINARIZATION
                for attr in data.domain.attributes):
            # No fallback in the script; widgets can prevent this error
            # by providing a fallback and issue a warning about doing so
            raise ValueError((_tr.m[74, "Exhaustive binarization does not handle "] + _tr.m[75, "attributes with more than {} values"]).
                             format(self.MAX_BINARIZATION))

        active_inst = np.nonzero(~np.isnan(data.Y))[0].astype(np.int32)
        root = self._build_tree(data, active_inst)
        if root is None:
            distr = distribution.Discrete(data, data.domain.class_var)
            if np.sum(distr) == 0:
                distr[:] = 1
            root = Node(None, 0, distr)
        root.subset = active_inst
        model = TreeModel(data, root)
        return model


class SklTreeClassifier(SklModel, TreeModelInterface):
    """Wrapper for SKL's tree classifier with the interface API for
    visualizations"""
    def __init__(self, *args, **kwargs):
        SklModel.__init__(self, *args, **kwargs)
        self._cached_sample_assignments = None


class SklTreeLearner(SklLearner):
    """Wrapper for SKL's tree inducer"""
    __wraps__ = skl_tree.DecisionTreeClassifier
    __returns__ = SklTreeClassifier
    name = 'tree'
    supports_weights = True

    def __init__(self, criterion="gini", splitter="best", max_depth=None,
                 min_samples_split=2, min_samples_leaf=1,
                 max_features=None,
                 random_state=None, max_leaf_nodes=None,
                 preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

```

## classification/random_forest.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
import sklearn.ensemble as skl_ensemble

from Orange.base import RandomForestModel
from Orange.classification import SklLearner, SklModel
from Orange.classification.tree import SklTreeClassifier
from Orange.data import Variable, DiscreteVariable
from Orange.preprocess.score import LearnerScorer

__all__ = ["RandomForestLearner"]


class _FeatureScorerMixin(LearnerScorer):
    feature_type = Variable
    class_type = DiscreteVariable

    def score(self, data):
        model = self(data)
        return model.skl_model.feature_importances_, model.domain.attributes


class RandomForestClassifier(SklModel, RandomForestModel):
    @property
    def trees(self):
        def wrap(tree, i):
            t = SklTreeClassifier(tree)
            t.domain = self.domain
            t.supports_multiclass = self.supports_multiclass
            t.name = _tr.m[56, "{} - tree {}"].format(self.name, i)
            t.original_domain = self.original_domain
            if hasattr(self, 'instances'):
                t.instances = self.instances
            return t

        return [wrap(tree, i)
                for i, tree in enumerate(self.skl_model.estimators_)]


class RandomForestLearner(SklLearner, _FeatureScorerMixin):
    __wraps__ = skl_ensemble.RandomForestClassifier
    __returns__ = RandomForestClassifier
    supports_weights = True

    def __init__(self,
                 n_estimators=10,
                 criterion="gini",
                 max_depth=None,
                 min_samples_split=2,
                 min_samples_leaf=1,
                 min_weight_fraction_leaf=0.,
                 max_features="sqrt",
                 max_leaf_nodes=None,
                 bootstrap=True,
                 oob_score=False,
                 n_jobs=1,
                 random_state=None,
                 verbose=0,
                 class_weight=None,
                 preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

```

## classification/gb.py

```python
# pylint: disable=unused-argument,too-many-arguments
from typing import Tuple

import numpy as np
import sklearn.ensemble as skl_ensemble

from Orange.classification import SklLearner, SklModel
from Orange.data import Variable, DiscreteVariable, Table
from Orange.preprocess.score import LearnerScorer

__all__ = ["GBClassifier"]


class _FeatureScorerMixin(LearnerScorer):
    feature_type = Variable
    class_type = DiscreteVariable

    def score(self, data: Table) -> Tuple[np.ndarray, Tuple[Variable]]:
        model: GBClassifier = self(data)
        return model.skl_model.feature_importances_, model.domain.attributes


class GBClassifier(SklLearner, _FeatureScorerMixin):
    __wraps__ = skl_ensemble.GradientBoostingClassifier
    __returns__ = SklModel
    supports_weights = True

    def __init__(self,
                 loss="log_loss",
                 learning_rate=0.1,
                 n_estimators=100,
                 subsample=1.0,
                 criterion="friedman_mse",
                 min_samples_split=2,
                 min_samples_leaf=1,
                 min_weight_fraction_leaf=0.,
                 max_depth=3,
                 min_impurity_decrease=0.,
                 min_impurity_split=None,
                 init=None,
                 random_state=None,
                 max_features=None,
                 verbose=0,
                 max_leaf_nodes=None,
                 warm_start=False,
                 presort="deprecated",
                 validation_fraction=0.1,
                 n_iter_no_change=None,
                 tol=1e-4,
                 ccp_alpha=0.0,
                 preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

```

## preprocess/preprocess.py

```python
"""
Preprocess
----------

"""
import numpy as np
import bottleneck as bn
import scipy.sparse as sp
from sklearn.impute import SimpleImputer

import Orange.data
from Orange.data.filter import HasClass
from Orange.statistics import distribution
from Orange.util import Reprable, Enum, deprecated
from . import impute, discretize, transformation

__all__ = ["Continuize", "Discretize", "Impute", "RemoveNaNRows",
           "SklImpute", "Normalize", "Randomize", "Preprocess",
           "RemoveConstant", "RemoveNaNClasses", "RemoveNaNColumns",
           "ProjectPCA", "ProjectCUR", "Scale", "RemoveSparse",
           "AdaptiveNormalize", "PreprocessorList"]


class Preprocess(Reprable):
    """
    A generic preprocessor base class.

    Methods
    -------
    __call__(data: Table) -> Table
        Return preprocessed data.
    """
    def __call__(self, data):
        raise NotImplementedError("Subclasses need to implement __call__")


class Continuize(Preprocess):
    MultinomialTreatment = Enum(
        "Continuize",
        ("Indicators", "FirstAsBase", "FrequentAsBase", "Remove",
         "RemoveMultinomial", "ReportError", "AsOrdinal", "AsNormalizedOrdinal",
         "Leave"),
        qualname="Continuize.MultinomialTreatment")
    (Indicators, FirstAsBase, FrequentAsBase, Remove, RemoveMultinomial,
     ReportError, AsOrdinal, AsNormalizedOrdinal, Leave) = MultinomialTreatment

    def __init__(self, zero_based=True,
                 multinomial_treatment=Indicators):
        self.zero_based = zero_based
        self.multinomial_treatment = multinomial_treatment

    def __call__(self, data):
        from . import continuize

        continuizer = continuize.DomainContinuizer(
            zero_based=self.zero_based,
            multinomial_treatment=self.multinomial_treatment)
        domain = continuizer(data)
        return data.transform(domain)


class Discretize(Preprocess):
    """
    Construct a discretizer, a preprocessor for discretization of
    continuous features.

    Parameters
    ----------
    method : discretization method (default: Orange.preprocess.discretize.Discretization)

    remove_const : bool (default=True)
        Determines whether the features with constant values are removed
        during discretization.
    """

    def __init__(self, method=None, remove_const=True,
                 discretize_classes=False, discretize_metas=False):
        self.method = method
        self.remove_const = remove_const
        self.discretize_classes = discretize_classes
        self.discretize_metas = discretize_metas

    def __call__(self, data):
        """
        Compute and apply discretization of the given data. Returns a new
        data table.

        Parameters
        ----------
        data : Orange.data.Table
            A data table to be discretized.
        """

        def transform(var):
            if var.is_continuous:
                new_var = method(data, var)
                if new_var is not None and \
                        (len(new_var.values) >= 2 or not self.remove_const):
                    return new_var
                else:
                    return None
            else:
                return var

        def discretized(vars_, do_discretize):
            if do_discretize:
                vars_ = (transform(var) for var in vars_)
                vars_ = [var for var in vars_ if var is not None]
            return vars_

        method = self.method or discretize.EqualFreq()
        domain = Orange.data.Domain(
            discretized(data.domain.attributes, True),
            discretized(data.domain.class_vars, self.discretize_classes),
            discretized(data.domain.metas, self.discretize_metas))
        return data.transform(domain)


class Impute(Preprocess):
    """
    Construct a imputer, a preprocessor for imputation of missing values in
    the data table.

    Parameters
    ----------
    method : imputation method (default: Orange.preprocess.impute.Average())
    """

    def __init__(self, method=Orange.preprocess.impute.Average()):
        self.method = method

    def __call__(self, data):
        """
        Apply an imputation method to the given dataset. Returns a new
        data table with missing values replaced by their imputations.

        Parameters
        ----------
        data : Orange.data.Table
            An input data table.
        """

        method = self.method or impute.Average()
        newattrs = [method(data, var) for var in data.domain.attributes]
        domain = Orange.data.Domain(
            newattrs, data.domain.class_vars, data.domain.metas)
        return data.transform(domain)


class SklImpute(Preprocess):
    __wraps__ = SimpleImputer

    def __init__(self, strategy='mean'):
        self.strategy = strategy

    def __call__(self, data):
        from Orange.data.sql.table import SqlTable
        if isinstance(data, SqlTable):
            return Impute()(data)
        imputer = SimpleImputer(strategy=self.strategy)
        imputer.fit(data.X)
        # Create new variables with appropriate `compute_value`, but
        # drop the ones which do not have valid `imputer.statistics_`
        # (i.e. all NaN columns). `sklearn.preprocessing.Imputer` already
        # drops them from the transformed X.
        features = [var.copy(compute_value=impute.ReplaceUnknowns(var, value))
                    for var, value in zip(data.domain.attributes,
                                          imputer.statistics_)
                    if not np.isnan(value)]
        domain = Orange.data.Domain(features, data.domain.class_vars,
                                    data.domain.metas)
        new_data = data.transform(domain)
        return new_data


class RemoveConstant(Preprocess):
    """
    Construct a preprocessor that removes features with constant values
    from the dataset.
    """

    def __call__(self, data):
        """
        Remove columns with constant values from the dataset and return
        the resulting data table.

        Parameters
        ----------
        data : an input dataset
        """

        oks = np.logical_and(~bn.allnan(data.X, axis=0),
                             bn.nanmin(data.X, axis=0) != bn.nanmax(data.X, axis=0))
        atts = [data.domain.attributes[i] for i, ok in enumerate(oks) if ok]
        domain = Orange.data.Domain(atts, data.domain.class_vars,
                                    data.domain.metas)
        return data.transform(domain)


class RemoveNaNRows(Preprocess):
    _reprable_module = True

    def __call__(self, data):
        mask = np.isnan(data.X)
        mask = np.any(mask, axis=1)
        return data[~mask]


class RemoveNaNColumns(Preprocess):
    """
    Remove features from the data domain if they contain
    `threshold` or more unknown values.

    `threshold` can be an integer or a float in the range (0, 1) representing
    the fraction of the data size. When not provided, columns with only missing
    values are removed (default).
    """
    def __init__(self, threshold=None):
        self.threshold = threshold

    def __call__(self, data, threshold=None):
        # missing entries in sparse data are treated as zeros so we skip removing NaNs
        if sp.issparse(data.X):
            return data

        if threshold is None:
            threshold = data.X.shape[0] if self.threshold is None else \
                        self.threshold
        if isinstance(threshold, float):
            threshold = threshold * data.X.shape[0]
        nans = np.sum(np.isnan(data.X), axis=0)
        att = [a for a, n in zip(data.domain.attributes, nans) if n < threshold]
        domain = Orange.data.Domain(att, data.domain.class_vars,
                                    data.domain.metas)
        return data.transform(domain)


@deprecated("Orange.data.filter.HasClas")
class RemoveNaNClasses(Preprocess):
    """
    Construct preprocessor that removes examples with missing class
    from the dataset.
    """

    def __call__(self, data):
        """
        Remove rows that contain NaN in any class variable from the dataset
        and return the resulting data table.

        Parameters
        ----------
        data : an input dataset

        Returns
        -------
        data : dataset without rows with missing classes
        """
        return HasClass()(data)


class Normalize(Preprocess):
    """
    Construct a preprocessor for normalization of features.
    Given a data table, preprocessor returns a new table in
    which the continuous attributes are normalized.

    Parameters
    ----------
    zero_based : bool (default=True)
        Only used when `norm_type=NormalizeBySpan`.

        Determines the value used as the “low” value of the variable.
        It determines the interval for normalized continuous variables
        (either [-1, 1] or [0, 1]).

    norm_type : NormTypes (default: Normalize.NormalizeBySD)
        Normalization type. If Normalize.NormalizeBySD, the values are
        replaced with standardized values by subtracting the average
        value and dividing by the standard deviation.
        Attribute zero_based has no effect on this standardization.

        If Normalize.NormalizeBySpan, the values are replaced with
        normalized values by subtracting min value of the data and
        dividing by span (max - min).

    transform_class : bool (default=False)
        If True the class is normalized as well.

    center : bool (default=True)
        Only used when `norm_type=NormalizeBySD`.

        Whether or not to center the data so it has mean zero.

    normalize_datetime : bool (default=False)


    Examples
    --------
    >>> from Orange.data import Table
    >>> from Orange.preprocess import Normalize
    >>> data = Table("iris")
    >>> normalizer = Normalize(norm_type=Normalize.NormalizeBySpan)
    >>> normalized_data = normalizer(data)
    """
    Type = Enum("Normalize", ("NormalizeBySpan", "NormalizeBySD"),
                qualname="Normalize.Type")
    NormalizeBySpan, NormalizeBySD = Type

    def __init__(self,
                 zero_based=True,
                 norm_type=NormalizeBySD,
                 transform_class=False,
                 center=True,
                 normalize_datetime=False):
        self.zero_based = zero_based
        self.norm_type = norm_type
        self.transform_class = transform_class
        self.center = center
        self.normalize_datetime = normalize_datetime

    def __call__(self, data):
        """
        Compute and apply normalization of the given data. Returns a new
        data table.

        Parameters
        ----------
        data : Orange.data.Table
            A data table to be normalized.

        Returns
        -------
        data : Orange.data.Table
            Normalized data table.
        """
        from . import normalize

        if all(a.attributes.get('skip-normalization', False)
               for a in data.domain.attributes if a.is_continuous):
            # Skip normalization for datasets where all features are marked as already normalized.
            # Required for SVMs (with normalizer as their default preprocessor) on sparse data to
            # retain sparse structure. Normalizing sparse data would otherwise result in a dense
            # matrix, which requires too much memory. For example, this is used for Bag of Words
            # models where normalization is not really needed.
            return data

        normalizer = normalize.Normalizer(
            zero_based=self.zero_based,
            norm_type=self.norm_type,
            transform_class=self.transform_class,
            center=self.center,
            normalize_datetime=self.normalize_datetime
        )
        return normalizer(data)


class Randomize(Preprocess):
    """
    Construct a preprocessor for randomization of classes,
    attributes and/or metas.
    Given a data table, preprocessor returns a new table in
    which the data is shuffled.

    Parameters
    ----------

    rand_type : RandTypes (default: Randomize.RandomizeClasses)
        Randomization type. If Randomize.RandomizeClasses, classes
        are shuffled.
        If Randomize.RandomizeAttributes, attributes are shuffled.
        If Randomize.RandomizeMetas, metas are shuffled.

    rand_seed : int (optional)
        Random seed

    Examples
    --------
    >>> from Orange.data import Table
    >>> from Orange.preprocess import Randomize
    >>> data = Table("iris")
    >>> randomizer = Randomize(Randomize.RandomizeClasses)
    >>> randomized_data = randomizer(data)
    """
    Type = Enum("Randomize",
                dict(RandomizeClasses=1,
                     RandomizeAttributes=2,
                     RandomizeMetas=4),
                type=int,
                qualname="Randomize.Type")
    RandomizeClasses, RandomizeAttributes, RandomizeMetas = Type

    def __init__(self, rand_type=RandomizeClasses, rand_seed=None):
        self.rand_type = rand_type
        self.rand_seed = rand_seed

    def __call__(self, data):
        """
        Apply randomization of the given data. Returns a new
        data table.

        Parameters
        ----------
        data : Orange.data.Table
            A data table to be randomized.

        Returns
        -------
        data : Orange.data.Table
            Randomized data table.
        """
        new_data = data.copy()
        rstate = np.random.RandomState(self.rand_seed)
        # ensure the same seed is not used to shuffle X and Y at the same time
        r1, r2, r3 = rstate.randint(0, 2 ** 32 - 1, size=3, dtype=np.int64)
        with new_data.unlocked():
            if self.rand_type & Randomize.RandomizeClasses:
                new_data.Y = self.randomize(new_data.Y, r1)
            if self.rand_type & Randomize.RandomizeAttributes:
                new_data.X = self.randomize(new_data.X, r2)
            if self.rand_type & Randomize.RandomizeMetas:
                new_data.metas = self.randomize(new_data.metas, r3)
        return new_data

    @staticmethod
    def randomize(table, rand_state=None):
        rstate = np.random.RandomState(rand_state)
        if sp.issparse(table):
            table = table.tocsc()  # type: sp.spmatrix
            for i in range(table.shape[1]):
                permutation = rstate.permutation(table.shape[0])
                col_indices = \
                    table.indices[table.indptr[i]: table.indptr[i + 1]]
                col_indices[:] = permutation[col_indices]
        elif len(table.shape) > 1:
            for i in range(table.shape[1]):
                rstate.shuffle(table[:, i])
        else:
            rstate.shuffle(table)
        return table


class ProjectPCA(Preprocess):

    def __init__(self, n_components=None):
        self.n_components = n_components

    def __call__(self, data):
        pca = Orange.projection.PCA(n_components=self.n_components)(data)
        return pca(data)


class ProjectCUR(Preprocess):

    def __init__(self, rank=3, max_error=1):
        self.rank = rank
        self.max_error = max_error

    def __call__(self, data):
        rank = min(self.rank, min(data.X.shape)-1)
        cur = Orange.projection.CUR(
            rank=rank, max_error=self.max_error,
            compute_U=False,
        )(data)
        return cur(data)


class Scale(Preprocess):
    """
    Scale data preprocessor.  Scales data so that its distribution remains
    the same but its location on the axis changes.
    """
    class _MethodEnum(Enum):
        def __call__(self, *args, **kwargs):
            return getattr(Scale, '_' + self.name)(*args, **kwargs)

    CenteringType = _MethodEnum("Scale", ("NoCentering", "Mean", "Median"),
                                qualname="Scale.CenteringType")
    ScalingType = _MethodEnum("Scale", ("NoScaling", "Std", "Span"),
                              qualname="Scale.ScalingType")
    NoCentering, Mean, Median = CenteringType
    NoScaling, Std, Span = ScalingType

    @staticmethod
    def _Mean(dist):
        values, counts = np.array(dist)
        return np.average(values, weights=counts)

    @staticmethod
    def _Median(dist):
        values, counts = np.array(dist)
        cumdist = np.cumsum(counts)
        if cumdist[-1] > 0:
            cumdist /= cumdist[-1]
        return np.interp(.5, cumdist, values)

    @staticmethod
    def _Std(dist):
        values, counts = np.array(dist)
        mean = np.average(values, weights=counts)
        diff = values - mean
        return np.sqrt(np.average(diff ** 2, weights=counts))

    @staticmethod
    def _Span(dist):
        values = np.array(dist[0])
        return np.max(values) - np.min(values)

    def __init__(self, center=Mean, scale=Std):
        self.center = center
        self.scale = scale

    def __call__(self, data):
        if self.center is None and self.scale is None:
            return data

        def transform(var):
            dist = distribution.get_distribution(data, var)
            if self.center != self.NoCentering:
                c = self.center(dist)
                dist[0, :] -= c
            else:
                c = 0

            if self.scale != self.NoScaling:
                s = self.scale(dist)
                if s < 1e-15:
                    s = 1
            else:
                s = 1
            factor = 1 / s
            transformed_var = var.copy(
                compute_value=transformation.Normalizer(var, c, factor))
            return transformed_var

        newvars = []
        for var in data.domain.attributes:
            if var.is_continuous:
                newvars.append(transform(var))
            else:
                newvars.append(var)
        domain = Orange.data.Domain(newvars, data.domain.class_vars,
                                    data.domain.metas)
        return data.transform(domain)


class PreprocessorList(Preprocess):
    """
    Store a list of preprocessors and on call apply them to the dataset.

    Parameters
    ----------
    preprocessors : list
        A list of preprocessors.
    """

    def __init__(self, preprocessors=()):
        self.preprocessors = list(preprocessors)

    def __call__(self, data):
        """
        Applies a list of preprocessors to the dataset.

        Parameters
        ----------
        data : an input data table
        """

        for pp in self.preprocessors:
            data = pp(data)
        return data

class RemoveSparse(Preprocess):
    """
    Filter out the features with too many (>threshold) zeros or missing values. Threshold is user defined.

    Parameters
    ----------
    threshold: int or float
        if >= 1, the argument represents the allowed number of 0s or NaNs;
        if below 1, it represents the allowed proportion of 0s or NaNs
    filter0: bool
        if True (default), preprocessor counts 0s, otherwise NaNs
    """
    def __init__(self, threshold=0.05, filter0=True):
        self.filter0 = filter0
        self.threshold = threshold

    def __call__(self, data):
        threshold = self.threshold
        if self.threshold < 1:
            threshold *= data.X.shape[0]

        if self.filter0:
            if sp.issparse(data.X):
                data_csc = sp.csc_matrix(data.X)
                h, w = data_csc.shape
                sparseness = [h - data_csc[:, i].count_nonzero()
                              for i in range(w)]
            else:
                sparseness = data.X.shape[0] - np.count_nonzero(data.X, axis=0)
        else:  # filter by nans
            if sp.issparse(data.X):
                data_csc = sp.csc_matrix(data.X)
                sparseness = [np.sum(np.isnan(data.X[:, i].data))
                              for i in range(data_csc.shape[1])]
            else:
                sparseness = np.sum(np.isnan(data.X), axis=0)
        att = [a for a, s in zip(data.domain.attributes, sparseness)
               if s <= threshold]
        domain = Orange.data.Domain(att, data.domain.class_vars,
                                    data.domain.metas)
        return data.transform(domain)


class AdaptiveNormalize(Preprocess):
    """
    Construct a preprocessors that normalizes or merely scales the data.
    If the input is sparse, data is only scaled, to avoid turning it to
    dense. Parameters are diveded to those passed to Normalize or Scale
    class. Scaling takes only scale parameter.
     If the user wants to have more options with scaling,
    they should use the preprocessing widget.
    For more details, check Scale and Normalize widget.

    Parameters
    ----------

    zero_based : bool (default=True)
        passed to Normalize

    norm_type : NormTypes (default: Normalize.NormalizeBySD)
        passed to Normalize

    transform_class : bool (default=False)
        passed to Normalize

    center : bool(default=True)
        passed to Normalize

    normalize_datetime : bool (default=False)
        passed to Normalize

    scale : ScaleTypes (default: Scale.Span)
        passed to Scale
    """

    def __init__(self,
                 zero_based=True,
                 norm_type=Normalize.NormalizeBySD,
                 transform_class=False,
                 normalize_datetime=False,
                 center=True,
                 scale=Scale.Span):
        self.normalize_pps = Normalize(zero_based,
                                       norm_type,
                                       transform_class,
                                       center,
                                       normalize_datetime)
        self.scale_pps = Scale(center=Scale.NoCentering, scale=scale)

    def __call__(self, data):
        if sp.issparse(data.X):
            return self.scale_pps(data)
        return self.normalize_pps(data)

```

## evaluation/testing.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
# __new__ methods have different arguments
# pylint: disable=arguments-differ
from warnings import warn
from collections import namedtuple
from itertools import chain
from time import time

import numpy as np

import sklearn.model_selection as skl

from Orange.data import Domain, ContinuousVariable, DiscreteVariable
from Orange.data.util import get_unique_names

__all__ = ["Results", "CrossValidation", "LeaveOneOut", "TestOnTrainingData",
           "ShuffleSplit", "TestOnTestData", "sample", "CrossValidationFeature"]

_MpResults = namedtuple('_MpResults', ('fold_i', 'learner_i', 'model',
                                       'failed', 'n_values', 'values',
                                       'probs', 'train_time', 'test_time'))


def _identity(x):
    return x


def _mp_worker(fold_i, train_data, test_data, learner_i, learner,
               store_models, suppresses_exceptions=True):
    predicted, probs, model, failed = None, None, None, False
    train_time, test_time = None, None
    try:
        if not train_data or not test_data:
            raise RuntimeError('Test fold is empty')
        # training
        t0 = time()
        model = learner(train_data)
        train_time = time() - t0
        t0 = time()
        # testing
        class_var = train_data.domain.class_var
        if class_var and class_var.is_discrete:
            predicted, probs = model(test_data, model.ValueProbs)
        else:
            predicted = model(test_data, model.Value)
        test_time = time() - t0
    # Different models can fail at any time raising any exception
    except Exception as ex:  # pylint: disable=broad-except
        if not suppresses_exceptions:
            raise ex
        failed = ex
    return _MpResults(fold_i, learner_i, store_models and model,
                      failed, len(test_data), predicted, probs,
                      train_time, test_time)


class Results:
    """
    Class for storing predictions in model testing.

    Attributes:
        data (Optional[Table]):  Data used for testing.

        models (Optional[List[Model]]): A list of induced models.

        row_indices (np.ndarray): Indices of rows in `data` that were used in
            testing, stored as a numpy vector of length `nrows`.
            Values of `actual[i]`, `predicted[i]` and `probabilities[i]` refer
            to the target value of instance, that is, the i-th test instance
            is `data[row_indices[i]]`, its actual class is `actual[i]`, and
            the prediction by m-th method is `predicted[m, i]`.

        nrows (int): The number of test instances (including duplicates);
            `nrows` equals the length of `row_indices` and `actual`, and the
            second dimension of `predicted` and `probabilities`.

        actual (np.ndarray): true values of target variable in a vector of
            length `nrows`.

        predicted (np.ndarray): predicted values of target variable in an array
            of shape (number-of-methods, `nrows`)

        probabilities (Optional[np.ndarray]): predicted probabilities
            (for discrete target variables) in an array of shape
            (number-of-methods, `nrows`, number-of-classes)

        folds (List[Slice or List[int]]): a list of indices (or slice objects)
            corresponding to testing data subsets, that is,
            `row_indices[folds[i]]` contains row indices used in fold i, so
            `data[row_indices[folds[i]]]` is the corresponding testing data

        train_time (np.ndarray): training times of batches

        test_time (np.ndarray): testing times of batches
    """
    def __init__(self, data=None, *,
                 nmethods=None, nrows=None, nclasses=None,
                 domain=None,
                 row_indices=None, folds=None, score_by_folds=True,
                 learners=None, models=None, failed=None,
                 actual=None, predicted=None, probabilities=None,
                 # pylint: disable=unused-argument
                 store_data=None, store_models=None,
                 train_time=None, test_time=None):
        """
        Construct an instance.

        The constructor stores the given data, and creates empty arrays
        `actual`, `predicted` and `probabilities` if ther are not given but
        sufficient data is provided to deduct their shapes.

        The function

        - set any attributes specified directly through arguments.
        - infers the number of methods, rows and classes from other data
           and/or check their overall consistency.
        - Prepare empty arrays `actual`, `predicted`, `probabilities` and
          `failed` if the are not given. If not enough data is available,
          the corresponding arrays are `None`.

        Args:
            data (Orange.data.Table): stored data from which test was sampled
            nmethods (int): number of methods; can be inferred (or must match)
                the size of `learners`, `models`, `failed`, `predicted` and
                `probabilities`
            nrows (int): number of data instances; can be inferred (or must
                match) `data`, `row_indices`, `actual`, `predicted` and
                `probabilities`
            nclasses (int): number of class values (`None` if continuous); can
                be inferred (or must match) from `domain.class_var` or
                `probabilities`
            domain (Orange.data.Domain): data domain; can be inferred (or must)
                match `data.domain`
            row_indices (np.ndarray): see class documentation
            folds (np.ndarray): see class documentation
            score_by_folds (np.ndarray): see class documentation
            learners (np.ndarray): see class documentation
            models (np.ndarray): see class documentation
            failed (list of str): see class documentation
            actual (np.ndarray): see class documentation
            predicted (np.ndarray): see class documentation
            probabilities (np.ndarray): see class documentation
            store_data (bool): ignored; kept for backward compatibility
            store_models (bool): ignored; kept for backward compatibility
        """

        # Set given data directly from arguments
        self.data = data
        self.domain = domain

        self.row_indices = row_indices
        self.folds = folds
        self.score_by_folds = score_by_folds

        self.learners = learners
        self.models = models

        self.actual = actual
        self.predicted = predicted
        self.probabilities = probabilities
        self.failed = failed

        self.train_time = train_time
        self.test_time = test_time

        # Guess the rest -- or check for ambguities
        def set_or_raise(value, exp_values, msg):
            for exp_value in exp_values:
                if exp_value is False:
                    continue
                if value is None:
                    value = exp_value
                elif value != exp_value:
                    raise ValueError(msg)
            return value
        domain = self.domain = set_or_raise(
            domain, [data is not None and data.domain],
            "mismatching domain")
        self.nrows = nrows = set_or_raise(
            nrows, [actual is not None and len(actual),
                    row_indices is not None and len(row_indices),
                    predicted is not None and predicted.shape[1],
                    probabilities is not None and probabilities.shape[1]],
            "mismatching number of rows")
        if domain is not None and domain.has_continuous_class:
            if nclasses is not None:
                raise ValueError(
                    "regression results cannot have non-None 'nclasses'")
            if probabilities is not None:
                raise ValueError(
                    "regression results cannot have 'probabilities'")
        nclasses = set_or_raise(
            nclasses, [domain is not None and domain.has_discrete_class and
                       len(domain.class_var.values),
                       probabilities is not None and probabilities.shape[2]],
            "mismatching number of class values")
        nmethods = set_or_raise(
            nmethods, [learners is not None and len(learners),
                       models is not None and models.shape[1],
                       failed is not None and len(failed),
                       predicted is not None and predicted.shape[0],
                       probabilities is not None and probabilities.shape[0]],
            "mismatching number of methods")

        # Prepare empty arrays
        if actual is None \
                and nrows is not None:
            self.actual = np.empty(nrows)

        if predicted is None \
                and nmethods is not None and nrows is not None:
            self.predicted = np.empty((nmethods, nrows))

        if probabilities is None \
                and nmethods is not None and nrows is not None \
                and nclasses is not None:
            self.probabilities = \
                np.empty((nmethods, nrows, nclasses))

        if failed is None \
                and nmethods is not None:
            self.failed = [False] * nmethods

    def get_fold(self, fold):
        results = Results()
        results.data = self.data

        if self.folds is None:
            raise ValueError("This 'Results' instance does not have folds.")

        if self.models is not None:
            results.models = self.models[fold]

        results.row_indices = self.row_indices[self.folds[fold]]
        results.actual = self.actual[self.folds[fold]]
        results.predicted = self.predicted[:, self.folds[fold]]
        results.domain = self.domain

        if self.probabilities is not None:
            results.probabilities = self.probabilities[:, self.folds[fold]]

        return results

    def get_augmented_data(self, model_names,
                           include_attrs=True, include_predictions=True,
                           include_probabilities=True):
        """
        Return the test data table augmented with meta attributes containing
        predictions, probabilities (if the task is classification) and fold
        indices.

        Args:
            model_names (list of str): names of models
            include_attrs (bool):
                if set to `False`, original attributes are removed
            include_predictions (bool):
                if set to `False`, predictions are not added
            include_probabilities (bool):
                if set to `False`, probabilities are not added

        Returns:
            augmented_data (Orange.data.Table):
                data augmented with predictions, probabilities and fold indices

        """
        assert self.predicted.shape[0] == len(model_names)

        data = self.data[self.row_indices]
        domain = data.domain
        class_var = domain.class_var
        classification = class_var and class_var.is_discrete

        new_meta_attr = []
        new_meta_vals = np.empty((len(data), 0))
        names = [var.name for var in chain(domain.attributes,
                                           domain.metas,
                                           domain.class_vars)]

        if classification:
            # predictions
            if include_predictions:
                uniq_new, names = self.create_unique_vars(names, model_names, class_var.values)
                new_meta_attr += uniq_new
                new_meta_vals = np.hstack((new_meta_vals, self.predicted.T))

            # probabilities
            if include_probabilities:
                proposed = [f"{name} ({value})" for name in model_names for value in class_var.values]

                uniq_new, names = self.create_unique_vars(names, proposed)
                new_meta_attr += uniq_new

                for i in self.probabilities:
                    new_meta_vals = np.hstack((new_meta_vals, i))

        elif include_predictions:
            # regression
            uniq_new, names = self.create_unique_vars(names, model_names)
            new_meta_attr += uniq_new
            new_meta_vals = np.hstack((new_meta_vals, self.predicted.T))

        # add fold info
        if self.folds is not None:
            values = [str(i + 1) for i in range(len(self.folds))]
            uniq_new, names = self.create_unique_vars(names, ["Fold"], values)
            new_meta_attr += uniq_new
            fold = np.empty((len(data), 1))
            for i, s in enumerate(self.folds):
                fold[s, 0] = i
            new_meta_vals = np.hstack((new_meta_vals, fold))

        # append new columns to meta attributes
        new_meta_attr = list(data.domain.metas) + new_meta_attr
        new_meta_vals = np.hstack((data.metas, new_meta_vals))

        attrs = data.domain.attributes if include_attrs else []
        domain = Domain(attrs, data.domain.class_vars, metas=new_meta_attr)
        predictions = data.transform(domain)
        with predictions.unlocked(predictions.metas):
            predictions.metas = new_meta_vals
        predictions.name = data.name
        return predictions

    def create_unique_vars(self, names, proposed_names, values=()):
        unique_vars = []
        for proposed in proposed_names:
            uniq = get_unique_names(names, proposed)
            if values:
                unique_vars.append(DiscreteVariable(uniq, values))
            else:
                unique_vars.append(ContinuousVariable(uniq))
            names.append(uniq)
        return unique_vars, names

    def split_by_model(self):
        """
        Split evaluation results by models.

        The method generates instances of `Results` containing data for single
        models
        """
        data = self.data
        nmethods = len(self.predicted)
        for i in range(nmethods):
            res = Results()
            res.data = data
            res.domain = self.domain
            res.learners = [self.learners[i]]
            res.row_indices = self.row_indices
            res.actual = self.actual
            res.folds = self.folds
            res.score_by_folds = self.score_by_folds
            res.test_time = self.test_time[i]
            res.train_time = self.train_time[i]

            res.predicted = self.predicted[(i,), :]
            if getattr(self, "probabilities", None) is not None:
                res.probabilities = self.probabilities[(i,), :, :]

            if self.models is not None:
                res.models = self.models[:, i:i + 1]

            res.failed = [self.failed[i]]
            yield res


class Validation:
    """
    Base class for different testing schemata such as cross validation and
    testing on separate data set.

    If `data` is some data table and `learners` is a list of learning
    algorithms. This will run 5-fold cross validation and store the results
    in `res`.

        cv = CrossValidation(k=5)
        res = cv(data, learners)

    If constructor was given data and learning algorithms (as in
    `res = CrossValidation(data, learners, k=5)`, it used to automagically
    call the instance after constructing it and return `Results` instead
    of an instance of `Validation`. This functionality
    is deprecated and will be removed in the future.

    Attributes:
        store_data (bool): a flag defining whether the data is stored
        store_models (bool): a flag defining whether the models are stored
    """
    score_by_folds = False

    def __new__(cls,
                data=None, learners=None, preprocessor=None, test_data=None,
                *, callback=None, store_data=False, store_models=False,
                n_jobs=None, **kwargs):
        self = super().__new__(cls)

        if (learners is None) != (data is None):
            raise ValueError(
                "learners and train_data must both be present or not")
        if learners is None:
            if preprocessor is not None:
                raise ValueError(("preprocessor cannot be given if learners " + "and train_data are omitted"))
            if callback is not None:
                raise ValueError(("callback cannot be given if learners " + "and train_data are omitted"))
            return self

        warn(("calling Validation's constructor with data and learners " + "is deprecated;\nconstruct an instance and call it"),
             DeprecationWarning, stacklevel=2)

        # Explicitly call __init__ because Python won't
        self.__init__(store_data=store_data, store_models=store_models,
                      **kwargs)
        if test_data is not None:
            test_data_kwargs = {"test_data": test_data}
        else:
            test_data_kwargs = {}
        return self(data, learners=learners, preprocessor=preprocessor,
                    callback=callback, **test_data_kwargs)

    # Note: this will be called only if __new__ doesn't have data and learners
    def __init__(self, *, store_data=False, store_models=False):
        self.store_data = store_data
        self.store_models = store_models

    def fit(self, *args, **kwargs):
        warn("Validation.fit is deprecated; use the call operator",
             DeprecationWarning)
        return self(*args, **kwargs)

    def __call__(self, data, learners, preprocessor=None, *, callback=None,
                 suppresses_exceptions=True):
        """
        Args:
            data (Orange.data.Table): data to be used (usually split) into
                training and testing
            learners (list of Orange.Learner): a list of learning algorithms
            preprocessor (Orange.preprocess.Preprocess): preprocessor applied
                on training data
            callback (Callable): a function called to notify about the progress
            suppresses_exceptions (bool): suppress the exceptions if True

        Returns:
            results (Result): results of testing
        """
        if preprocessor is None:
            preprocessor = _identity
        if callback is None:
            callback = _identity
        indices = self.get_indices(data)
        folds, row_indices, actual = self.prepare_arrays(data, indices)

        data_splits = (
            (fold_i, preprocessor(data[train_i]), data[test_i])
            for fold_i, (train_i, test_i) in enumerate(indices))
        args_iter = (
            (fold_i, data, test_data, learner_i, learner, self.store_models)
            for (fold_i, data, test_data) in data_splits
            for (learner_i, learner) in enumerate(learners))

        part_results = []
        parts = np.linspace(.0, .99, len(learners) * len(indices) + 1)[1:]
        for progress, part in zip(parts, args_iter):
            part_results.append(
                _mp_worker(*(part + ()),
                           suppresses_exceptions=suppresses_exceptions)
            )
            callback(progress)
        callback(1)

        results = Results(
            data=data if self.store_data else None,
            domain=data.domain,
            nrows=len(row_indices), learners=learners,
            row_indices=row_indices, folds=folds, actual=actual,
            score_by_folds=self.score_by_folds,
            train_time=np.zeros((len(learners),)),
            test_time=np.zeros((len(learners),)))

        if self.store_models:
            results.models = np.tile(None, (len(indices), len(learners)))
        self._collect_part_results(results, part_results)
        return results

    @classmethod
    def prepare_arrays(cls, data, indices):
        """Prepare `folds`, `row_indices` and `actual`.

        The method is used by `__call__`. While functional, it may be
        overriden in subclasses for speed-ups.

        Args:
            data (Orange.data.Table): data use for testing
            indices (list of vectors):
                indices of data instances in each test sample

        Returns:
            folds: (np.ndarray): see class documentation
            row_indices: (np.ndarray): see class documentation
            actual: (np.ndarray): see class documentation
        """
        folds = []
        row_indices = []

        ptr = 0
        for _, test in indices:
            folds.append(slice(ptr, ptr + len(test)))
            row_indices.append(test)
            ptr += len(test)

        row_indices = np.concatenate(row_indices, axis=0)
        return folds, row_indices, data[row_indices].Y

    @staticmethod
    def get_indices(data):
        """
        Return a list of arrays of indices of test data instance

        For example, in k-fold CV, the result is a list with `k` elements,
        each containing approximately `len(data) / k` nonoverlapping indices
        into `data`.

        This method is abstract and must be implemented in derived classes
        unless they provide their own implementation of the `__call__`
        method.

        Args:
            data (Orange.data.Table): test data

        Returns:
            indices (list of np.ndarray):
                a list of arrays of indices into `data`
        """
        raise NotImplementedError()

    def _collect_part_results(self, results, part_results):
        part_results = sorted(part_results)

        ptr, prev_fold_i, prev_n_values = 0, 0, 0
        for res in part_results:
            if res.fold_i != prev_fold_i:
                ptr += prev_n_values
                prev_fold_i = res.fold_i
            result_slice = slice(ptr, ptr + res.n_values)
            prev_n_values = res.n_values

            if res.failed:
                results.failed[res.learner_i] = res.failed
                continue

            if len(res.values.shape) > 1 and res.values.shape[1] > 1:
                msg = _tr.m[126, "Multiple targets are not supported."]
                results.failed[res.learner_i] = ValueError(msg)
                continue

            if self.store_models:
                results.models[res.fold_i][res.learner_i] = res.model

            results.predicted[res.learner_i][result_slice] = res.values
            results.train_time[res.learner_i] += res.train_time
            results.test_time[res.learner_i] += res.test_time
            if res.probs is not None:
                results.probabilities[res.learner_i][result_slice, :] = \
                    res.probs


class CrossValidation(Validation):
    """
    K-fold cross validation

    Attributes:
        k (int): number of folds (default: 10)
        random_state (int):
            seed for random number generator (default: 0). If set to `None`,
            a different seed is used each time
        stratified (bool):
            flag deciding whether to perform stratified cross-validation.
            If `True` but the class sizes don't allow it, it uses non-stratified
            validataion and adds a list `warning` with a warning message(s) to
            the `Result`.
    """
    # TODO: list `warning` contains just repetitions of the same message
    #       replace with a flag in `Results`?
    def __init__(self, k=10, stratified=True, random_state=0,
                 store_data=False, store_models=False, warnings=None):
        super().__init__(store_data=store_data, store_models=store_models)
        self.k = k
        self.stratified = stratified
        self.random_state = random_state
        self.warnings = [] if warnings is None else warnings

    def get_indices(self, data):
        if self.stratified and data.domain.has_discrete_class:
            try:
                splitter = skl.StratifiedKFold(
                    self.k, shuffle=True, random_state=self.random_state
                )
                splitter.get_n_splits(data.X, data.Y)
                return list(splitter.split(data.X, data.Y))
            except ValueError:
                self.warnings.append("Using non-stratified sampling.")

        splitter = skl.KFold(
            self.k, shuffle=True, random_state=self.random_state)
        splitter.get_n_splits(data)
        return list(splitter.split(data))


class CrossValidationFeature(Validation):
    """
    Cross validation with folds according to values of a feature.

    Attributes:
        feature (Orange.data.Variable): the feature defining the folds
    """
    def __init__(self, feature=None,
                 store_data=False, store_models=False, warnings=None):
        super().__init__(store_data=store_data, store_models=store_models)
        self.feature = feature

    def get_indices(self, data):
        data = data.transform(Domain([self.feature], None))
        values = data[:, self.feature].X
        indices = []
        for v in range(len(self.feature.values)):
            test_index = np.where(values == v)[0]
            train_index = np.where((values != v) & (~np.isnan(values)))[0]
            if test_index.size and train_index.size:
                indices.append((train_index, test_index))
        if not indices:
            raise ValueError(
                (f"'{self.feature.name}' does not have at least two distinct " + "values on the data"))
        return indices


class LeaveOneOut(Validation):
    """Leave-one-out testing"""
    score_by_folds = False

    def get_indices(self, data):
        splitter = skl.LeaveOneOut()
        splitter.get_n_splits(data)
        return list(splitter.split(data))

    @staticmethod
    def prepare_arrays(data, indices):
        # sped up version of super().prepare_arrays(data)
        row_indices = np.arange(len(data))
        return row_indices, row_indices, data.Y.flatten()


class ShuffleSplit(Validation):
    """
    Test by repeated random sampling

    Attributes:
        n_resamples (int): number of repetitions
        test_size (float, int, None):
            If float, should be between 0.0 and 1.0 and represent the proportion
            of the dataset to include in the test split. If int, represents the
            absolute number of test samples. If None, the value is set to the
            complement of the train size. By default, the value is set to 0.1.
            The default will change in version 0.21. It will remain 0.1 only
            if ``train_size`` is unspecified, otherwise it will complement
            the specified ``train_size``.
            (from documentation of scipy.sklearn.StratifiedShuffleSplit)

        train_size : float, int, or None, default is None
            If float, should be between 0.0 and 1.0 and represent the
            proportion of the dataset to include in the train split. If
            int, represents the absolute number of train samples. If None,
            the value is automatically set to the complement of the test size.
            (from documentation of scipy.sklearn.StratifiedShuffleSplit)

        stratified (bool):
            flag deciding whether to perform stratified cross-validation.

        random_state (int):
            seed for random number generator (default: 0). If set to `None`,
            a different seed is used each time

    """
    def __init__(self, n_resamples=10, train_size=None, test_size=0.1,
                 stratified=True, random_state=0,
                 store_data=False, store_models=False):
        super().__init__(store_data=store_data, store_models=store_models)
        self.n_resamples = n_resamples
        self.train_size = train_size
        self.test_size = test_size
        self.stratified = stratified
        self.random_state = random_state

    def get_indices(self, data):
        if self.stratified and data.domain.has_discrete_class:
            splitter = skl.StratifiedShuffleSplit(
                n_splits=self.n_resamples, train_size=self.train_size,
                test_size=self.test_size, random_state=self.random_state
            )
            splitter.get_n_splits(data.X, data.Y)
            return list(splitter.split(data.X, data.Y))

        splitter = skl.ShuffleSplit(
            n_splits=self.n_resamples, train_size=self.train_size,
            test_size=self.test_size, random_state=self.random_state
        )
        splitter.get_n_splits(data)
        return list(splitter.split(data))


class TestOnTestData(Validation):
    """
    Test on separately provided test data

    Note that the class has a different signature for `__call__`.
    """
    # get_indices is not needed in this class, pylint: disable=abstract-method

    def __new__(cls, data=None, test_data=None, learners=None,
                preprocessor=None, **kwargs):
        if "train_data" in kwargs:
            if data is None:
                data = kwargs.pop("train_data")
            else:
                raise ValueError(
                    "argument 'data' is given twice (once as 'train_data')")
        return super().__new__(
            cls,
            data=data, learners=learners, preprocessor=preprocessor,
            test_data=test_data, **kwargs)

    def __call__(self, data, test_data, learners, preprocessor=None,
                 *, callback=None, suppresses_exceptions=True):
        """
        Args:
            data (Orange.data.Table): training data
            test_data (Orange.data.Table): test_data
            learners (list of Orange.Learner): a list of learning algorithms
            preprocessor (Orange.preprocess.Preprocess): preprocessor applied
                on training data
            callback (Callable): a function called to notify about the progress
            suppresses_exceptions (bool): suppress the exceptions if True

        Returns:
            results (Result): results of testing
        """
        if preprocessor is None:
            preprocessor = _identity
        if callback is None:
            callback = _identity

        train_data = preprocessor(data)
        part_results = []
        for (learner_i, learner) in enumerate(learners):
            part_results.append(
                _mp_worker(0, train_data, test_data, learner_i, learner,
                           self.store_models, suppresses_exceptions))
            callback((learner_i + 1) / len(learners))
        callback(1)

        results = Results(
            data=test_data if self.store_data else None,
            domain=test_data.domain,
            nrows=len(test_data), learners=learners,
            row_indices=np.arange(len(test_data)),
            folds=(Ellipsis, ),
            actual=test_data.Y,
            score_by_folds=self.score_by_folds,
            train_time=np.zeros((len(learners),)),
            test_time=np.zeros((len(learners),)))

        if self.store_models:
            results.models = np.tile(None, (1, len(learners)))
        self._collect_part_results(results, part_results)
        return results


class TestOnTrainingData(TestOnTestData):
    """Test on training data"""
    # get_indices is not needed in this class, pylint: disable=abstract-method
    # signature is such as on the base class, pylint: disable=signature-differs
    def __new__(cls, data=None, learners=None, preprocessor=None, **kwargs):
        return super().__new__(
            cls,
            data, test_data=data, learners=learners, preprocessor=preprocessor,
            **kwargs)

    def __call__(self, data, learners, preprocessor=None, *, callback=None,
                 suppresses_exceptions=True, **kwargs):
        kwargs.setdefault("test_data", data)
        # if kwargs contains anything besides test_data, this will be detected
        # (and complained about) by super().__call__
        return super().__call__(
            data=data, learners=learners, preprocessor=preprocessor,
            callback=callback, suppresses_exceptions=suppresses_exceptions,
            **kwargs)


def sample(table, n=0.7, stratified=False, replace=False,
           random_state=None):
    """
    Samples data instances from a data table. Returns the sample and
    a dataset from input data table that are not in the sample. Also
    uses several sampling functions from
    `scikit-learn <http://scikit-learn.org>`_.

    table : data table
        A data table from which to sample.

    n : float, int (default = 0.7)
        If float, should be between 0.0 and 1.0 and represents
        the proportion of data instances in the resulting sample. If
        int, n is the number of data instances in the resulting sample.

    stratified : bool, optional (default = False)
        If true, sampling will try to consider class values and
        match distribution of class values
        in train and test subsets.

    replace : bool, optional (default = False)
        sample with replacement

    random_state : int or RandomState
        Pseudo-random number generator state used for random sampling.
    """

    if isinstance(n, float):
        n = int(n * len(table))

    if replace:
        if random_state is None:
            rgen = np.random
        else:
            rgen = np.random.mtrand.RandomState(random_state)
        a_sample = rgen.randint(0, len(table), n)
        o = np.ones(len(table))
        o[a_sample] = 0
        others = np.nonzero(o)[0]
        return table[a_sample], table[others]

    n = len(table) - n
    if stratified and table.domain.has_discrete_class:
        test_size = max(len(table.domain.class_var.values), n)
        splitter = skl.StratifiedShuffleSplit(
            n_splits=1, test_size=test_size, train_size=len(table) - test_size,
            random_state=random_state)
        splitter.get_n_splits(table.X, table.Y)
        ind = splitter.split(table.X, table.Y)
    else:
        splitter = skl.ShuffleSplit(
            n_splits=1, test_size=n, random_state=random_state)
        splitter.get_n_splits(table)
        ind = splitter.split(table)
    ind = next(ind)
    return table[ind[0]], table[ind[1]]

```

## base.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
import inspect
import itertools
from collections.abc import Iterable
import re
import warnings
from typing import Callable, Optional, NamedTuple, Type

import numpy as np
import scipy

from Orange.data import Table, Storage, Instance, Value, Domain
from Orange.data.filter import HasClass
from Orange.data.table import DomainTransformationError
from Orange.data.util import one_hot
from Orange.misc.environ import cache_dir
from Orange.misc.wrapper_meta import WrapperMeta
from Orange.preprocess import Continuize, RemoveNaNColumns, SklImpute, Normalize
from Orange.statistics.util import all_nan
from Orange.util import Reprable, OrangeDeprecationWarning, wrap_callback, \
    dummy_callback


__all__ = ["Learner", "Model", "SklLearner", "SklModel",
           "ReprableWithPreprocessors"]


class ReprableWithPreprocessors(Reprable):
    def _reprable_omit_param(self, name, default, value):
        if name == "preprocessors":
            default_cls = type(self).preprocessors
            if value is default or value is default_cls:
                return True
            else:
                try:
                    return all(p1 is p2 for p1, p2 in
                               itertools.zip_longest(value, default_cls))
                except (ValueError, TypeError):
                    return False
        else:
            return super()._reprable_omit_param(name, default, value)


class Learner(ReprableWithPreprocessors):
    """The base learner class.

    Preprocessors can behave in a number of different ways, all of which are
    described here.
    If the user does not pass a preprocessor argument into the Learner
    constructor, the default learner preprocessors are used. We assume the user
    would simply like to get things done without having to worry about
    preprocessors.
    If the user chooses to pass in their own preprocessors, we assume they know
    what they are doing. In this case, only the user preprocessors are used and
    the default preprocessors are ignored.
    In case the user would like to use the default preprocessors as well as
    their own ones, the `use_default_preprocessors` flag should be set.

    Parameters
    ----------
    preprocessors : Preprocessor or tuple[Preprocessor], optional
        User defined preprocessors. If the user specifies their own
        preprocessors, the default ones will not be used, unless the
        `use_default_preprocessors` flag is set.

    Attributes
    ----------
    preprocessors : tuple[Preprocessor] (default None)
        The used defined preprocessors that will be used on any data.
    use_default_preprocessors : bool (default False)
        This flag indicates whether to use the default preprocessors that are
        defined on the Learner class. Since preprocessors can be applied in a
        number of ways
    active_preprocessors : tuple[Preprocessor]
        The processors that will be used when data is passed to the learner.
        This depends on whether the user has passed in their own preprocessors
        and whether the `use_default_preprocessors` flag is set.

        This property is needed mainly because of the `Fitter` class, which can
        not know in advance, which preprocessors it will need to use. Therefore
        this resolves the active preprocessors using a lazy approach.
    params : dict
        The params that the learner is constructed with.

    """
    supports_multiclass = False
    supports_weights = False
    #: A sequence of data preprocessors to apply on data prior to
    #: fitting the model
    preprocessors = ()

    class FittedParameter(NamedTuple):
        name: str
        label: str
        type: Type
        min: Optional[int] = None
        max: Optional[int] = None

    # Note: Do not use this class attribute.
    #       It remains here for compatibility reasons.
    learner_adequacy_err_msg = ''

    def __init__(self, preprocessors=None):
        self.use_default_preprocessors = False
        if isinstance(preprocessors, Iterable):
            self.preprocessors = tuple(preprocessors)
        elif preprocessors:
            self.preprocessors = (preprocessors,)

    # pylint: disable=R0201
    def fit(self, X, Y, W=None):
        raise RuntimeError(
            "Descendants of Learner must overload method fit or fit_storage")

    def fit_storage(self, data):
        """Default implementation of fit_storage defaults to calling fit.
        Derived classes must define fit_storage or fit"""
        X, Y, W = data.X, data.Y, data.W if data.has_weights() else None
        return self.fit(X, Y, W)

    def __call__(self, data, progress_callback=None):
        reason = self.incompatibility_reason(data.domain)
        if reason is not None:
            raise ValueError(reason)

        origdomain = data.domain

        if isinstance(data, Instance):
            data = Table(data.domain, [data])
        origdata = data

        if progress_callback is None:
            progress_callback = dummy_callback
        progress_callback(0, _tr.m[2, "Preprocessing..."])
        try:
            cb = wrap_callback(progress_callback, end=0.1)
            data = self.preprocess(data, progress_callback=cb)
        except TypeError:
            data = self.preprocess(data)
            warnings.warn(("A keyword argument 'progress_callback' has been " + ("added to the preprocess() signature. Implementing " + ("the method without the argument is deprecated and " + "will result in an error in the future."))),
                          OrangeDeprecationWarning)

        if len(data.domain.class_vars) > 1 and not self.supports_multiclass:
            raise TypeError("%s doesn't support multiple class variables" %
                            self.__class__.__name__)

        progress_callback(0.1, _tr.m[3, "Fitting..."])
        model = self._fit_model(data)
        model.used_vals = [np.unique(y).astype(int) for y in data.Y[:, None].T]
        if not hasattr(model, "domain") or model.domain is None:
            # some models set domain themself and it should be respected
            # e.g. calibration learners set the base_learner's domain which
            # would be wrongly overwritten if we set it here for any model
            model.domain = data.domain
        model.supports_multiclass = self.supports_multiclass
        model.name = self.name
        model.original_domain = origdomain
        model.original_data = origdata
        progress_callback(1)
        return model

    def _fit_model(self, data):
        if type(self).fit is Learner.fit:
            return self.fit_storage(data)
        else:
            X, Y, W = data.X, data.Y, data.W if data.has_weights() else None
            return self.fit(X, Y, W)

    def preprocess(self, data, progress_callback=None):
        """Apply the `preprocessors` to the data"""
        if progress_callback is None:
            progress_callback = dummy_callback
        n_pps = len(list(self.active_preprocessors))
        for i, pp in enumerate(self.active_preprocessors):
            progress_callback(i / n_pps)
            data = pp(data)
        progress_callback(1)
        return data

    @property
    def active_preprocessors(self):
        yield from self.preprocessors
        if (self.use_default_preprocessors and
                self.preprocessors is not type(self).preprocessors):
            yield from type(self).preprocessors

    @property
    def fitted_parameters(self) -> list:
        return []

    # pylint: disable=no-self-use
    def incompatibility_reason(self, _: Domain) -> Optional[str]:
        """Return None if a learner can fit domain or string explaining why it can not."""
        return None

    @property
    def name(self):
        """Return a short name derived from Learner type name"""
        try:
            return self.__name
        except AttributeError:
            name = self.__class__.__name__
            if name.endswith('Learner'):
                name = name[:-len('Learner')]
            if name.endswith('Fitter'):
                name = name[:-len('Fitter')]
            if isinstance(self, SklLearner) and name.startswith('Skl'):
                name = name[len('Skl'):]
            name = name or 'learner'
            # From http://stackoverflow.com/a/1176023/1090455 <3
            self.name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2',
                               re.sub(r'(.)([A-Z][a-z]+)', r'\1 \2', name)).lower()
            return self.name

    @name.setter
    def name(self, value):
        self.__name = value

    def __str__(self):
        return self.name


class Model(Reprable):
    supports_multiclass = False
    supports_weights = False
    Value = 0
    Probs = 1
    ValueProbs = 2

    def __init__(self, domain=None, original_domain=None):
        self.domain = domain
        if original_domain is not None:
            self.original_domain = original_domain
        else:
            self.original_domain = domain
        self.used_vals = None

    def predict(self, X):
        if type(self).predict_storage is Model.predict_storage:
            raise TypeError("Descendants of Model must overload method predict")
        else:
            Y = np.zeros((len(X), len(self.domain.class_vars)))
            Y[:] = np.nan
            table = Table(self.domain, X, Y)
            return self.predict_storage(table)

    def predict_storage(self, data):
        if isinstance(data, Storage):
            return self.predict(data.X)
        elif isinstance(data, Instance):
            return self.predict(np.atleast_2d(data.x))
        raise TypeError("Unrecognized argument (instance of '{}')"
                        .format(type(data).__name__))

    def get_backmappers(self, data):
        backmappers = []
        n_values = []

        dataclasses = data.domain.class_vars
        modelclasses = self.domain.class_vars
        if not (modelclasses and dataclasses):
            return None, []  # classless model or data; don't touch
        if len(dataclasses) != len(modelclasses):
            raise DomainTransformationError(
                "Mismatching number of model's classes and data classes")
        for dataclass, modelclass in zip(dataclasses, modelclasses):
            if dataclass != modelclass:
                if dataclass.name != modelclass.name:
                    raise DomainTransformationError(
                        (f"Model for '{modelclass.name}' " + f"cannot predict '{dataclass.name}'"))
                else:
                    raise DomainTransformationError(
                        (f"Variables '{modelclass.name}' in the model is " + ("incompatible with the variable of the same name " + "in the data.")))
            n_values.append(dataclass.is_discrete and len(dataclass.values))
            if dataclass is not modelclass and dataclass.is_discrete:
                backmappers.append(dataclass.get_mapper_from(modelclass))
            else:
                backmappers.append(None)
        if all(x is None for x in backmappers):
            backmappers = None
        return backmappers, n_values

    def backmap_value(self, value, mapped_probs, n_values, backmappers):
        if backmappers is None:
            return value

        if value.ndim == 2:  # For multitarget, recursive call by columns
            new_value = np.zeros(value.shape)
            for i, n_value, backmapper in zip(
                    itertools.count(), n_values, backmappers):
                new_value[:, i] = self.backmap_value(
                    value[:, i], mapped_probs[:, i, :], [n_value], [backmapper])
            return new_value

        backmapper = backmappers[0]
        if backmapper is None:
            return value

        value = backmapper(value)
        nans = np.isnan(value)
        if not np.any(nans) or n_values[0] < 2:
            return value
        if mapped_probs is not None:
            value[nans] = np.argmax(mapped_probs[nans], axis=1)
        else:
            value[nans] = np.random.RandomState(0).choice(
                backmapper(np.arange(0, n_values[0] - 1)),
                (np.sum(nans), ))
        return value

    def backmap_probs(self, probs, n_values, backmappers):
        if backmappers is None:
            return probs

        if probs.ndim == 3:
            new_probs = np.zeros((len(probs), len(n_values), max(n_values)),
                                 dtype=probs.dtype)
            for i, n_value, backmapper in zip(
                    itertools.count(), n_values, backmappers):
                new_probs[:, i, :n_value] = self.backmap_probs(
                    probs[:, i, :], [n_value], [backmapper])
            return new_probs

        backmapper = backmappers[0]
        if backmapper is None:
            return probs
        n_value = n_values[0]
        new_probs = np.zeros((len(probs), n_value), dtype=probs.dtype)
        for col in range(probs.shape[1]):
            target = backmapper(col)
            if not np.isnan(target):
                new_probs[:, int(target)] = probs[:, col]
        tots = np.sum(new_probs, axis=1)
        zero_sum = tots == 0
        new_probs[zero_sum] = 1
        tots[zero_sum] = n_value
        new_probs = new_probs / tots[:, None]
        return new_probs

    def data_to_model_domain(
            self, data: Table, progress_callback: Callable = dummy_callback
    ) -> Table:
        """
        Transforms data to the model domain if possible.

        Parameters
        ----------
        data
            Data to be transformed to the model domain
        progress_callback
            Callback - callable - to report the progress

        Returns
        -------
        Transformed data table

        Raises
        ------
        DomainTransformationError
            Error indicates that transformation is not possible since domains
            are not compatible
        """
        if data.domain == self.domain:
            return data

        progress_callback(0)
        if self.original_domain.attributes != data.domain.attributes \
                and data.X.size \
                and not all_nan(data.X):
            progress_callback(0.5)
            new_data = data.transform(self.original_domain)
            if all_nan(new_data.X):
                raise DomainTransformationError(
                    "domain transformation produced no defined values")
            progress_callback(0.75)
            data = new_data.transform(self.domain)
            progress_callback(1)
            return data

        progress_callback(0.5)
        data = data.transform(self.domain)
        progress_callback(1)
        return data

    def __call__(self, data, ret=Value):
        multitarget = len(self.domain.class_vars) > 1

        def one_hot_probs(value):
            if not multitarget:
                return one_hot(
                    value,
                    dim=len(self.domain.class_var.values)
                    if self.domain is not None else None
                )

            max_card = max(len(c.values) for c in self.domain.class_vars)
            probs = np.zeros(value.shape + (max_card,), float)
            for i in range(len(self.domain.class_vars)):
                probs[:, i, :] = one_hot(value[:, i])
            return probs

        def extend_probabilities(probs):
            """
            Since SklModels and models implementing `fit` and not `fit_storage`
            do not guarantee correct prediction dimensionality, extend
            dimensionality of probabilities when it does not match the number
            of values in the domain.
            """
            class_vars = self.domain.class_vars
            max_values = max(len(cv.values) for cv in class_vars)
            if max_values == probs.shape[-1]:
                return probs

            if not self.supports_multiclass:
                probs = probs[:, np.newaxis, :]

            probs_ext = np.zeros((len(probs), len(class_vars), max_values))
            for c, used_vals in enumerate(self.used_vals):
                for i, cv in enumerate(used_vals):
                    probs_ext[:, c, cv] = probs[:, c, i]

            if not self.supports_multiclass:
                probs_ext = probs_ext[:, 0, :]
            return probs_ext

        def fix_dim(x):
            return x[0] if one_d else x

        if not 0 <= ret <= 2:
            raise ValueError("invalid value of argument 'ret'")
        if ret > 0 and any(v.is_continuous for v in self.domain.class_vars):
            raise ValueError("cannot predict continuous distributions")

        # Convert 1d structures to 2d and remember doing it
        one_d = True
        if isinstance(data, Instance):
            data = Table.from_list(data.domain, [data])
        elif isinstance(data, (list, tuple)) \
                and not isinstance(data[0], (list, tuple)):
            data = [data]
        elif isinstance(data, np.ndarray) and data.ndim == 1:
            data = np.atleast_2d(data)
        else:
            one_d = False

        # if sparse convert to csr_matrix
        if scipy.sparse.issparse(data):
            data = data.tocsr()

        # Call the predictor
        backmappers = None
        n_values = []
        if isinstance(data, (np.ndarray, scipy.sparse.csr_matrix)):
            prediction = self.predict(data)
        elif isinstance(data, Table):
            backmappers, n_values = self.get_backmappers(data)
            data = self.data_to_model_domain(data)
            prediction = self.predict_storage(data)
        elif isinstance(data, (list, tuple)):
            data = Table.from_list(self.original_domain, data)
            data = data.transform(self.domain)
            prediction = self.predict_storage(data)
        else:
            raise TypeError("Unrecognized argument (instance of '{}')"
                            .format(type(data).__name__))

        # Parse the result into value and probs
        if isinstance(prediction, tuple):
            value, probs = prediction
        elif prediction.ndim == 1 + multitarget:
            value, probs = prediction, None
        elif prediction.ndim == 2 + multitarget:
            value, probs = None, prediction
        else:
            raise TypeError(f"model returned a {prediction.ndim}-dimensional array")

        # Ensure that we have what we need to return; backmap everything
        if probs is None and (ret != Model.Value or backmappers is not None):
            probs = one_hot_probs(value)
        if probs is not None:
            probs = extend_probabilities(probs)
            probs = self.backmap_probs(probs, n_values, backmappers)
        if ret != Model.Probs:
            if value is None:
                value = np.argmax(probs, axis=-1)
                # probs are already backmapped
            else:
                value = self.backmap_value(value, probs, n_values, backmappers)

        # Return what we need to
        if ret == Model.Probs:
            return fix_dim(probs)
        if isinstance(data, Instance) and not multitarget:
            value = [Value(self.domain.class_var, value[0])]
        if ret == Model.Value:
            return fix_dim(value)
        else:  # ret == Model.ValueProbs
            return fix_dim(value), fix_dim(probs)

    def __getstate__(self):
        """Skip (possibly large) data when pickling models"""
        state = self.__dict__
        if 'original_data' in state:
            state = state.copy()
            state['original_data'] = None
        return state


class SklModel(Model, metaclass=WrapperMeta):
    used_vals = None

    def __init__(self, skl_model):
        self.skl_model = skl_model

    def predict(self, X):
        value = self.skl_model.predict(X)
        # SVM has probability attribute which defines if method compute probs
        has_prob_attr = hasattr(self.skl_model, "probability")
        if (has_prob_attr and self.skl_model.probability
                or not has_prob_attr
                and hasattr(self.skl_model, "predict_proba")):
            probs = self.skl_model.predict_proba(X)
            return value, probs
        return value

    def __repr__(self):
        # Params represented as a comment because not passed into constructor
        return super().__repr__() + '  # params=' + repr(self.params)


class SklLearner(Learner, metaclass=WrapperMeta):
    """
    ${skldoc}
    Additional Orange parameters

    preprocessors : list, optional
        An ordered list of preprocessors applied to data before
        training or testing.
        Defaults to
        `[RemoveNaNClasses(), Continuize(), SklImpute(), RemoveNaNColumns()]`
    """
    __wraps__ = None
    __returns__ = SklModel
    _params = {}

    preprocessors = default_preprocessors = [
        HasClass(),
        Continuize(),
        RemoveNaNColumns(),
        SklImpute()]

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, value):
        self._params = self._get_sklparams(value)

    def _get_sklparams(self, values):
        skllearner = self.__wraps__
        if skllearner is not None:
            spec = list(
                inspect.signature(skllearner.__init__).parameters.keys()
            )
            # first argument is 'self'
            assert spec[0] == "self"
            params = {
                name: values[name] for name in spec[1:] if name in values
            }
        else:
            raise TypeError("Wrapper does not define '__wraps__'")
        return params

    def preprocess(self, data, progress_callback=None):
        data = super().preprocess(data, progress_callback)

        if any(v.is_discrete and len(v.values) > 2
               for v in data.domain.attributes):
            raise ValueError("Wrapped scikit-learn methods do not support " +
                             "multinomial variables.")

        return data

    def __call__(self, data, progress_callback=None):
        m = super().__call__(data, progress_callback)
        m.params = self.params
        return m

    def _initialize_wrapped(self):
        # pylint: disable=not-callable
        return self.__wraps__(**self.params)

    def fit(self, X, Y, W=None):
        clf = self._initialize_wrapped()
        Y = Y.reshape(-1)
        if W is None or not self.supports_weights:
            return self.__returns__(clf.fit(X, Y))
        return self.__returns__(clf.fit(X, Y, sample_weight=W.reshape(-1)))

    def __getattr__(self, item):
        try:
            return self.params[item]
        except (KeyError, AttributeError):
            raise AttributeError(item) from None

    # TODO: Disallow (or mirror) __setattr__ for keys in params?

    def __dir__(self):
        dd = super().__dir__()
        return list(sorted(set(dd) | set(self.params.keys())))


class TreeModel(Model):
    pass


class RandomForestModel(Model):
    """Interface for random forest models
    """

    @property
    def trees(self):
        """Return a list of Trees in the forest

        Returns
        -------
        List[Tree]
        """


class KNNBase:
    """Base class for KNN (classification and regression) learners
    """

    # pylint: disable=unused-argument
    def __init__(self, n_neighbors=5, metric="euclidean", weights="uniform",
                 algorithm='auto', metric_params=None,
                 preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

    def fit(self, X, Y, W=None):
        if self.params["metric_params"] is None and \
                        self.params.get("metric") == "mahalanobis":
            self.params["metric_params"] = {"V": np.cov(X.T)}
        return super().fit(X, Y, W)


class NNBase:
    """Base class for neural network (classification and regression) learners
    """
    preprocessors = SklLearner.preprocessors + [Normalize()]

    # pylint: disable=unused-argument,too-many-arguments
    def __init__(self, hidden_layer_sizes=(100,), activation='relu',
                 solver='adam', alpha=0.0001, batch_size='auto',
                 learning_rate='constant', learning_rate_init=0.001,
                 power_t=0.5, max_iter=200, shuffle=True, random_state=None,
                 tol=0.0001, verbose=False, warm_start=False, momentum=0.9,
                 nesterovs_momentum=True, early_stopping=False,
                 validation_fraction=0.1, beta_1=0.9, beta_2=0.999,
                 epsilon=1e-08, preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()


class CatGBModel(Model, metaclass=WrapperMeta):
    def __init__(self, cat_model, cat_features, domain):
        super().__init__(domain)
        self.cat_model = cat_model
        self.cat_features = cat_features

    def __call__(self, data, ret=Model.Value):
        if isinstance(data, Table):
            with data.force_unlocked(data.X):
                return super().__call__(data, ret)
        else:
            return super().__call__(data, ret)

    def predict(self, X):
        if self.cat_features:
            X = X.astype(str)
        value = self.cat_model.predict(X).flatten()
        if hasattr(self.cat_model, "predict_proba"):
            probs = self.cat_model.predict_proba(X)
            return value, probs
        return value

    def __repr__(self):
        # Params represented as a comment because not passed into constructor
        return super().__repr__() + '  # params=' + repr(self.params)


class CatGBBaseLearner(Learner, metaclass=WrapperMeta):
    """
    ${skldoc}
    Additional Orange parameters

    preprocessors : list, optional
        An ordered list of preprocessors applied to data before
        training or testing.
        Defaults to
        `[RemoveNaNClasses(), RemoveNaNColumns()]`
    """
    supports_weights = True
    __wraps__ = None
    __returns__ = CatGBModel
    _params = {}
    preprocessors = default_preprocessors = [
        HasClass(),
        RemoveNaNColumns(),
    ]

    # pylint: disable=unused-argument,too-many-arguments,too-many-locals
    def __init__(self,
                 iterations=None,
                 learning_rate=None,
                 depth=None,
                 l2_leaf_reg=None,
                 model_size_reg=None,
                 rsm=None,
                 loss_function=None,
                 border_count=None,
                 feature_border_type=None,
                 per_float_feature_quantization=None,
                 input_borders=None,
                 output_borders=None,
                 fold_permutation_block=None,
                 od_pval=None,
                 od_wait=None,
                 od_type=None,
                 nan_mode=None,
                 counter_calc_method=None,
                 leaf_estimation_iterations=None,
                 leaf_estimation_method=None,
                 thread_count=None,
                 random_seed=None,
                 use_best_model=None,
                 verbose=False,
                 logging_level=None,
                 metric_period=None,
                 ctr_leaf_count_limit=None,
                 store_all_simple_ctr=None,
                 max_ctr_complexity=None,
                 has_time=None,
                 allow_const_label=None,
                 classes_count=None,
                 class_weights=None,
                 one_hot_max_size=None,
                 random_strength=None,
                 name=None,
                 ignored_features=None,
                 train_dir=cache_dir(),
                 custom_loss=None,
                 custom_metric=None,
                 eval_metric=None,
                 bagging_temperature=None,
                 save_snapshot=None,
                 snapshot_file=None,
                 snapshot_interval=None,
                 fold_len_multiplier=None,
                 used_ram_limit=None,
                 gpu_ram_part=None,
                 allow_writing_files=False,
                 final_ctr_computation_mode=None,
                 approx_on_full_history=None,
                 boosting_type=None,
                 simple_ctr=None,
                 combinations_ctr=None,
                 per_feature_ctr=None,
                 task_type=None,
                 device_config=None,
                 devices=None,
                 bootstrap_type=None,
                 subsample=None,
                 sampling_unit=None,
                 dev_score_calc_obj_block_size=None,
                 max_depth=None,
                 n_estimators=None,
                 num_boost_round=None,
                 num_trees=None,
                 colsample_bylevel=None,
                 random_state=None,
                 reg_lambda=None,
                 objective=None,
                 eta=None,
                 max_bin=None,
                 scale_pos_weight=None,
                 gpu_cat_features_storage=None,
                 data_partition=None,
                 metadata=None,
                 early_stopping_rounds=None,
                 cat_features=None,
                 grow_policy=None,
                 min_data_in_leaf=None,
                 min_child_samples=None,
                 max_leaves=None,
                 num_leaves=None,
                 score_function=None,
                 leaf_estimation_backtracking=None,
                 ctr_history_unit=None,
                 monotone_constraints=None,
                 feature_weights=None,
                 penalties_coefficient=None,
                 first_feature_use_penalties=None,
                 model_shrink_rate=None,
                 model_shrink_mode=None,
                 langevin=None,
                 diffusion_temperature=None,
                 posterior_sampling=None,
                 boost_from_average=None,
                 text_features=None,
                 tokenizers=None,
                 dictionaries=None,
                 feature_calcers=None,
                 text_processing=None,
                 preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.params = vars()

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, value):
        self._params = self._get_wrapper_params(value)

    def _get_wrapper_params(self, values):
        spec = list(inspect.signature(
            self.__wraps__.__init__).parameters.keys())
        return {name: values[name] for name in spec[1:] if name in values}

    def __call__(self, data, progress_callback=None):
        m = super().__call__(data, progress_callback)
        m.params = self.params
        return m

    def fit_storage(self, data: Table):
        with data.force_unlocked(data.X):
            domain, X, Y, W = data.domain, data.X, data.Y.reshape(-1), None
            if self.supports_weights and data.has_weights():
                W = data.W.reshape(-1)
            # pylint: disable=not-callable
            clf = self.__wraps__(**self.params)
            cat_features = [i for i, attr in enumerate(domain.attributes)
                            if attr.is_discrete]
            if cat_features:
                X = X.astype(str)
            cat_model = clf.fit(X, Y, cat_features=cat_features, sample_weight=W)
            return self.__returns__(cat_model, cat_features, domain)

    def __getattr__(self, item):
        try:
            return self.params[item]
        except (KeyError, AttributeError):
            raise AttributeError(item) from None

    def __dir__(self):
        dd = super().__dir__()
        return list(sorted(set(dd) | set(self.params.keys())))


class XGBBase(SklLearner):
    """Base class for xgboost (classification and regression) learners """
    preprocessors = default_preprocessors = [
        HasClass(),
        Continuize(),
        RemoveNaNColumns(),
    ]

    def __init__(self, preprocessors=None, **kwargs):
        super().__init__(preprocessors=preprocessors)
        self.params = kwargs

    @SklLearner.params.setter
    def params(self, values: dict):
        self._params = values

```

## modelling/base.py

```python
import numpy as np

# pylint: disable=unused-import
from Orange.base import Learner, Model, SklLearner
from Orange.data import Table, Domain


class Fitter(Learner):
    """Handle multiple types of target variable with one learner.

    Subclasses of this class serve as a sort of dispatcher. When subclassing,
    we provide a `dict` which contain actual learner classes that handle
    appropriate data types. The fitter can then be used on any data and will
    delegate the work to the appropriate learner.

    If the learners that handle each data type require different parameters,
    you should pass in all the possible parameters to the fitter. The fitter
    will then determine which parameters have to be passed to individual
    learners.

    """
    __fits__ = {}
    __returns__ = Model

    # Constants to indicate what kind of problem we're dealing with
    CLASSIFICATION, REGRESSION = 'classification', 'regression'

    def __init__(self, preprocessors=None, **kwargs):
        super().__init__(preprocessors=preprocessors)
        self.kwargs = kwargs
        # Make sure to pass preprocessor params to individual learners
        self.kwargs['preprocessors'] = preprocessors
        self.__learners = {self.CLASSIFICATION: None, self.REGRESSION: None}

    def _fit_model(self, data):
        learner = self.get_learner(data)

        if type(self).fit is Learner.fit:
            return learner.fit_storage(data)
        else:
            X, Y, W = data.X, data.Y, data.W if data.has_weights() else None
            return learner.fit(X, Y, W)

    def preprocess(self, data, progress_callback=None):
        return self.get_learner(data).preprocess(data, progress_callback)

    def get_learner(self, problem_type):
        """Get the learner for a given problem type.

        Parameters
        ----------
        problem_type: str or Table or Domain
            If str, one of ``'classification'`` or ``'regression'``. If Table
            or Domain, the type is inferred from Domain's first class variable.

        Returns
        -------
        Learner
            The appropriate learner for the given problem type.

        Raises
        ------
        TypeError
            When (inferred) problem type not one of ``'classification'``
            or ``'regression'``.
        """
        if isinstance(problem_type, Table):
            problem_type = problem_type.domain
        if isinstance(problem_type, Domain):
            problem_type = (self.CLASSIFICATION if problem_type.has_discrete_class else
                            self.REGRESSION if problem_type.has_continuous_class else
                            None)
        # Prevent trying to access the learner when problem type is None
        if problem_type not in self.__fits__:
            raise TypeError("No learner to handle '{}'".format(problem_type))
        if self.__learners[problem_type] is None:
            learner = self.__fits__[problem_type](**self.__kwargs(problem_type))
            learner.use_default_preprocessors = self.use_default_preprocessors
            self.__learners[problem_type] = learner
        return self.__learners[problem_type]

    def __kwargs(self, problem_type):
        learner_kwargs = set(
            self.__fits__[problem_type].__init__.__code__.co_varnames[1:])
        changed_kwargs = self._change_kwargs(self.kwargs, problem_type)
        return {k: v for k, v in changed_kwargs.items() if k in learner_kwargs}

    def _change_kwargs(self, kwargs, problem_type):
        """Handle the kwargs to be passed to the learner before they are used.

        In some cases we need to manipulate the kwargs that will be passed to
        the learner, e.g. SGD takes a `loss` parameter in both the regression
        and classification learners, but the learner widget cannot
        differentiate between these two, so it passes classification and
        regression loss parameters individually. The appropriate one must be
        renamed into `loss` before passed to the actual learner instance. This
        is done here.

        """
        return kwargs

    @property
    def supports_weights(self):
        """The fitter supports weights if both the classification and
        regression learners support weights."""
        return (
            getattr(self.get_learner(self.CLASSIFICATION), 'supports_weights', False) and
            getattr(self.get_learner(self.REGRESSION), 'supports_weights', False)
        )

    @property
    def params(self):
        raise TypeError(
            'A fitter does not have its own params. If you need to access '
            'learner params, please use the `get_params` method.')

    def get_params(self, problem_type):
        """Access the specific learner params of a given learner."""
        return self.get_learner(problem_type).params


class SklFitter(Fitter):
    def _fit_model(self, data):
        model = super()._fit_model(data)
        model.used_vals = [np.unique(y).astype(int) for y in data.Y[:, None].T]
        model.params = self.get_params(data)
        return model

```

## evaluation/scoring.py

```python
"""
Methods for scoring prediction results (CA, AUC, ...).

Examples
--------
>>> import Orange
>>> data = Orange.data.Table('iris')
>>> learner = Orange.classification.LogisticRegressionLearner()
>>> results = Orange.evaluation.TestOnTrainingData(data, [learner])

"""
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator

import math
import warnings

import numpy as np
import sklearn.metrics as skl_metrics
from sklearn.metrics import confusion_matrix

from Orange.data import DiscreteVariable, ContinuousVariable, Domain
from Orange.misc.wrapper_meta import WrapperMeta
from Orange.util import OrangeDeprecationWarning


__all__ = ["CA", "Precision", "Recall", "F1", "PrecisionRecallFSupport", "AUC",
           "MSE", "RMSE", "MAE", "MAPE", "SMAPE", "R2", "LogLoss",
           "MatthewsCorrCoefficient"]


class ScoreMetaType(WrapperMeta):
    """
    Maintain a registry of non-abstract subclasses and assign the default
    value of `name`.

    The existing meta class Registry cannot be used since a meta class cannot
    have multiple inherited __new__ methods."""
    def __new__(mcs, name, bases, dict_, **kwargs):
        cls = WrapperMeta.__new__(mcs, name, bases, dict_)
        # Essentially `if cls is not Score`, except that Score may not exist yet
        if hasattr(cls, "registry"):
            if not kwargs.get("abstract"):
                # Don't use inherited names, look into dict_
                cls.name = dict_.get("name", name)
                cls.long_name = dict_.get("long_name", cls.name)
                cls.registry[name] = cls
        else:
            cls.registry = {}
        return cls

    def __init__(cls, *args, **_):
        WrapperMeta.__init__(cls, *args)


class Score(metaclass=ScoreMetaType):
    """
    ${sklpar}
    Parameters
    ----------
    results : Orange.evaluation.Results
        Stored predictions and actual data in model testing.
    """
    __wraps__ = None

    separate_folds = False
    is_scalar = True
    is_binary = False  #: If true, compute_score accepts `target` and `average`
    #: If the class doesn't explicitly contain `abstract=True`, it is not
    #: abstract; essentially, this attribute is not inherited
    abstract = True
    class_types = ()
    name = None
    long_name = None  #: A short user-readable name (e.g. a few words)

    default_visible = True
    priority = 100

    def __new__(cls, results=None, **kwargs):
        self = super().__new__(cls)
        if results is not None:
            self.__init__()
            return self(results, **kwargs)
        else:
            return self

    def __call__(self, results, **kwargs):
        if self.separate_folds and results.score_by_folds and results.folds:
            scores = self.scores_by_folds(results, **kwargs)
            return self.average(scores)

        return self.compute_score(results, **kwargs)

    def average(self, scores):
        if self.is_scalar:
            return np.mean(scores, axis=0)
        return NotImplementedError

    def scores_by_folds(self, results, **kwargs):
        nfolds = len(results.folds)
        nmodels = len(results.predicted)
        if self.is_scalar:
            scores = np.empty((nfolds, nmodels), dtype=np.float64)
        else:
            scores = [None] * nfolds
        for fold in range(nfolds):
            fold_results = results.get_fold(fold)
            scores[fold] = self.compute_score(fold_results, **kwargs)
        return scores

    def compute_score(self, results):
        wraps = type(self).__wraps__  # self.__wraps__ is invisible
        if wraps:
            return self.from_predicted(results, wraps)
        else:
            return NotImplementedError

    @staticmethod
    def from_predicted(results, score_function, **kwargs):
        def as_scalar(e):
            if np.isscalar(e):
                return e
            elif len(e) == 1:
                return e[0]
            else:
                raise ValueError("len(e) > 1")

        scores = (score_function(results.actual, predicted, **kwargs)
                  for predicted in results.predicted)
        # np.fromiter needs flat iter of scalars, some scoring function calls
        # return array of single element
        return np.fromiter(
            map(as_scalar, scores),
            dtype=np.float64, count=len(results.predicted))

    @staticmethod
    def is_compatible(domain: Domain) -> bool:
        raise NotImplementedError


class ClassificationScore(Score, abstract=True):
    class_types = (DiscreteVariable, )

    @staticmethod
    def is_compatible(domain: Domain) -> bool:
        return domain.has_discrete_class


class RegressionScore(Score, abstract=True):
    class_types = (ContinuousVariable, )

    @staticmethod
    def is_compatible(domain: Domain) -> bool:
        return domain.has_continuous_class


# pylint: disable=invalid-name
class CA(ClassificationScore):
    __wraps__ = skl_metrics.accuracy_score
    name = _tr.m[97, "CA"]
    long_name = _tr.m[98, "Classification accuracy"]
    priority = 20


class PrecisionRecallFSupport(ClassificationScore):
    __wraps__ = skl_metrics.precision_recall_fscore_support
    is_scalar = False


class TargetScore(ClassificationScore):
    """
    Base class for scorers that need a target value (a "positive" class).

    Parameters
    ----------
    results : Orange.evaluation.Results
        Stored predictions and actual data in model testing.

    target : int, optional (default=None)
        Target class value.
        When None:
          - if averaging is specified, use all classes and average results
          - if average is 'binary' and class variable has exactly 2 values,
            use the value '1' as the positive class

    average: str, method for averaging (default='binary')
        Default requires a binary class or target to be set.
        Options: 'weighted', 'macro', 'micro', None

    """
    is_binary = True
    abstract = True
    __wraps__ = None  # Subclasses should set the scoring function

    def compute_score(self, results, target=None, average='binary'):
        if average == 'binary':
            if target is None:
                if len(results.domain.class_var.values) > 2:
                    raise ValueError(
                        ("Multiclass data: specify target class or select " + "averaging ('weighted', 'macro', 'micro')"))
                target = 1  # Default: use 1 as "positive" class
            average = None
        labels = None if target is None else [target]
        return self.from_predicted(
            results, type(self).__wraps__, labels=labels, average=average)


class Precision(TargetScore):
    __wraps__ = skl_metrics.precision_score
    name = _tr.m[99, "Prec"]
    long_name = _tr.m[100, "Precision"]
    priority = 40


class Recall(TargetScore):
    __wraps__ = skl_metrics.recall_score
    name = long_name = _tr.m[101, "Recall"]
    priority = 50


class F1(TargetScore):
    __wraps__ = skl_metrics.f1_score
    name = long_name = _tr.m[102, "F1"]
    priority = 30


class AUC(ClassificationScore):
    """
    ${sklpar}

    Parameters
    ----------
    results : Orange.evaluation.Results
        Stored predictions and actual data in model testing.

    target : int, optional (default=None)
        Value of class to report.
    """
    __wraps__ = skl_metrics.roc_auc_score
    separate_folds = True
    is_binary = True
    name = _tr.m[103, "AUC"]
    long_name = _tr.m[104, "Area under ROC curve"]
    priority = 10

    @staticmethod
    def calculate_weights(results):
        classes = np.unique(results.actual)
        class_cases = [sum(results.actual == class_)
                       for class_ in classes]
        N = results.actual.shape[0]
        weights = np.array([c * (N - c) for c in class_cases])
        wsum = np.sum(weights)
        if wsum == 0:
            raise ValueError(_tr.m[105, "Class variable has less than two values"])
        else:
            return weights / wsum

    @staticmethod
    def single_class_auc(results, target):
        y = np.array(results.actual == target, dtype=int)
        return np.fromiter(
            (skl_metrics.roc_auc_score(y, probabilities[:, int(target)])
             for probabilities in results.probabilities),
            dtype=np.float64, count=len(results.predicted))

    def multi_class_auc(self, results):
        classes = np.unique(results.actual)
        weights = self.calculate_weights(results)
        auc_array = np.array([self.single_class_auc(results, class_)
                              for class_ in classes])
        return np.sum(auc_array.T * weights, axis=1)

    def compute_score(self, results, target=None, average=None):
        domain = results.domain
        n_classes = len(domain.class_var.values)

        if n_classes < 2:
            raise ValueError(_tr.m[106, "Class variable has less than two values"])
        elif n_classes == 2:
            return self.single_class_auc(results, 1)
        else:
            if target is None:
                return self.multi_class_auc(results)
            else:
                return self.single_class_auc(results, target)


class LogLoss(ClassificationScore):
    """
    ${sklpar}

    Parameters
    ----------
    results : Orange.evaluation.Results
        Stored predictions and actual data in model testing.

    eps : float
        Log loss is undefined for p=0 or p=1, so probabilities are
        clipped to max(eps, min(1 - eps, p)).

    normalize : bool, optional (default=True)
        If true, return the mean loss per sample.
        Otherwise, return the sum of the per-sample losses.

    sample_weight : array-like of shape = [n_samples], optional
        Sample weights.

    Examples
    --------
    >>> Orange.evaluation.LogLoss(results)
    array([0.1...])

    """
    __wraps__ = skl_metrics.log_loss
    priority = 120
    name = _tr.m[107, "LogLoss"]
    long_name = _tr.m[108, "Logistic loss"]
    default_visible = False

    def compute_score(self, results, eps=_tr.m[109, "auto"], normalize=True,
                      sample_weight=None):
        if eps != _tr.m[110, "auto"]:
            # eps argument will be removed in scikit-learn 1.5
            warnings.warn(
                (_tr.m[111, "`LogLoss.compute_score`: eps parameter is unused. "] + _tr.m[112, "It will always have value of `np.finfo(y_pred.dtype).eps`."]),
                OrangeDeprecationWarning,
            )
        return np.fromiter(
            (skl_metrics.log_loss(results.actual,
                                  probabilities,
                                  normalize=normalize,
                                  sample_weight=sample_weight)
             for probabilities in results.probabilities),
            dtype=np.float64, count=len(results.probabilities))


class Specificity(ClassificationScore):
    is_binary = True
    priority = 110
    name = "Spec"
    long_name = _tr.m[113, "Specificity"]
    default_visible = False

    @staticmethod
    def calculate_weights(results):
        classes, counts = np.unique(results.actual, return_counts=True)
        n = np.array(results.actual).shape[0]
        return counts / n, classes

    @staticmethod
    def specificity(y_true, y_pred):
        tn, fp, _, _ = confusion_matrix(y_true, y_pred).ravel()
        return tn / (tn + fp)

    def single_class_specificity(self, results, target):
        y_true = (np.array(results.actual) == target).astype(int)
        return np.fromiter(
            (self.specificity(y_true,
                              np.array(predicted == target, dtype=int))
             for predicted in results.predicted),
            dtype=np.float64, count=len(results.predicted))

    def multi_class_specificity(self, results):
        weights, classes = self.calculate_weights(results)
        scores = np.array([self.single_class_specificity(results, class_)
                           for class_ in classes])
        return np.sum(scores.T * weights, axis=1)

    def compute_score(self, results, target=None, average="binary"):
        domain = results.domain
        n_classes = len(domain.class_var.values)

        if target is None:
            if average == "weighted":
                return self.multi_class_specificity(results)
            elif average == "binary":  # average is binary
                if n_classes != 2:
                    raise ValueError(
                        (_tr.m[114, "Binary averaging needs two classes in data: "] + (_tr.m[115, "specify target class or use "] + _tr.m[116, "weighted averaging."])))
                return self.single_class_specificity(results, 1)
            else:
                raise ValueError(
                    ("Wrong parameters: For averaging select one of the " + "following values: ('weighted', 'binary')"))
        elif target is not None:
            return self.single_class_specificity(results, target)


class MatthewsCorrCoefficient(ClassificationScore):
    __wraps__ = skl_metrics.matthews_corrcoef
    name = "MCC"
    long_name = _tr.m[117, "Matthews correlation coefficient"]


# Regression scores


class MSE(RegressionScore):
    __wraps__ = skl_metrics.mean_squared_error
    name = "MSE"
    long_name = _tr.m[118, "Mean square error"]
    priority = 20


class RMSE(RegressionScore):
    name = "RMSE"
    long_name = _tr.m[119, "Root mean square error"]

    def compute_score(self, results):
        return np.sqrt(MSE(results))
    priority = 30


class MAE(RegressionScore):
    __wraps__ = skl_metrics.mean_absolute_error
    name = "MAE"
    long_name = _tr.m[120, "Mean absolute error"]
    priority = 40


class MAPE(RegressionScore):
    name = "MAPE"
    long_name = _tr.m[121, "Mean absolute percentage error"]
    priority = 45

    @staticmethod
    def __wraps__(actual, predicted):
        if np.any(actual == 0):
            return np.inf
        return np.sum(np.abs((actual - predicted) / actual)) / len(actual) * 100


class SMAPE(RegressionScore):
    name = "sMAPE"
    long_name = _tr.m[122, "Symmetric mean absolute percentage error"]
    priority = 45

    @staticmethod
    def __wraps__(actual, predicted):
        diff = np.abs(actual - predicted)
        summ = np.abs(actual) + np.abs(predicted)
        # To avoid 0 / 0, set divisor to 1; error will be 0, as it should be
        summ[summ == 0] = 1.0
        error = diff / summ
        return 2 * np.sum(error) / len(actual) * 100


# pylint: disable=invalid-name
class R2(RegressionScore):
    __wraps__ = skl_metrics.r2_score
    name = "R2"
    long_name = _tr.m[123, "Coefficient of determination"]
    priority = 50


class CVRMSE(RegressionScore):
    name = "CVRMSE"
    long_name = _tr.m[124, "Coefficient of variation of the RMSE"]
    priority = 110
    default_visible = False

    def compute_score(self, results):
        mean = np.nanmean(results.actual)
        if mean < 1e-10:
            raise ValueError(_tr.m[125, "Mean value is too small"])
        return RMSE(results) / mean * 100

```

## widgets/data/owpreprocess.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from collections import OrderedDict
import importlib.resources

import numpy

from AnyQt.QtWidgets import (
    QWidget, QButtonGroup, QGroupBox, QRadioButton, QSlider,
    QDoubleSpinBox, QComboBox, QSpinBox, QListView, QLabel,
    QScrollArea, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSizePolicy, QApplication, QCheckBox
)

from AnyQt.QtGui import (
    QIcon, QStandardItemModel, QStandardItem
)

from AnyQt.QtCore import (
    Qt, QEvent, QSize, QMimeData, QTimer
)

from AnyQt.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

from orangewidget.gui import Slider

import Orange.data
from Orange import preprocess
from Orange.preprocess import Continuize, ProjectPCA, RemoveNaNRows, \
    ProjectCUR, Scale as _Scale, Randomize as _Randomize, RemoveSparse
from Orange.widgets import widget, gui
from Orange.widgets.utils.localization import pl
from Orange.widgets.settings import Setting
from Orange.widgets.utils.overlay import OverlayWidget
from Orange.widgets.utils.sql import check_sql_input
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Input, Output
from Orange.preprocess import Normalize
from Orange.widgets.data.utils.preprocess import (
    BaseEditor, blocked, StandardItemModel, DescriptionRole,
    ParametersRole, Controller, SequenceFlow
)


class _NoneDisc(preprocess.discretize.Discretization):
    """Discretize all variables into None.

    Used in combination with preprocess.Discretize to remove
    all discrete features from the domain.

    """
    _reprable_module = True

    def __call__(self, data, variable):
        return None


class DiscretizeEditor(BaseEditor):
    """
    Editor for preprocess.Discretize.
    """
    #: Discretize methods
    NoDisc, EqualWidth, EqualFreq, Drop, EntropyMDL = 0, 1, 2, 3, 4
    Discretizers = {
        NoDisc: (None, {}),
        EqualWidth: (preprocess.discretize.EqualWidth, {"n": 4}),
        EqualFreq:  (preprocess.discretize.EqualFreq, {"n": 4}),
        Drop: (_NoneDisc, {}),
        EntropyMDL: (preprocess.discretize.EntropyMDL, {"force": False})
    }
    Names = {
        NoDisc: _tr.m[1248, "None"],
        EqualWidth: _tr.m[1249, "Equal width discretization"],
        EqualFreq: _tr.m[1250, "Equal frequency discretization"],
        Drop: _tr.m[1251, "Remove numeric features"],
        EntropyMDL: _tr.m[1252, "Entropy-MDL discretization"]
    }

    def __init__(self, parent=None, **kwargs):
        BaseEditor.__init__(self, parent, **kwargs)
        self.__method = DiscretizeEditor.EqualFreq
        self.__nintervals = 4

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.__group = group = QButtonGroup(self, exclusive=True)

        for method in [self.EntropyMDL, self.EqualFreq, self.EqualWidth,
                       self.Drop]:
            rb = QRadioButton(
                self, text=self.Names[method],
                checked=self.__method == method
            )
            layout.addWidget(rb)
            group.addButton(rb, method)

        group.buttonClicked.connect(self.__on_buttonClicked)

        self.__slbox = slbox = QGroupBox(
            title=_tr.m[1253, "Number of intervals (for equal width/frequency)"],
            flat=True
        )
        slbox.setLayout(QHBoxLayout())
        self.__slider = slider = Slider(
            orientation=Qt.Horizontal,
            minimum=2, maximum=10, value=self.__nintervals,
            enabled=self.__method in [self.EqualFreq, self.EqualWidth],
            pageStep=1, tickPosition=QSlider.TicksBelow
        )
        slider.valueChanged.connect(self.__on_valueChanged)
        slbox.layout().addWidget(slider)
        self.__slabel = slabel = QLabel()
        slbox.layout().addWidget(slabel)

        container = QHBoxLayout()
        container.setContentsMargins(13, 0, 0, 0)
        container.addWidget(slbox)
        self.layout().insertLayout(3, container)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

    def setMethod(self, method):
        if self.__method != method:
            self.__method = method
            b = self.__group.button(method)
            b.setChecked(True)
            self.__slider.setEnabled(
                method in [self.EqualFreq, self.EqualWidth]
            )
            self.changed.emit()

    def method(self):
        return self.__method

    def intervals(self):
        return self.__nintervals

    def setIntervals(self, n):
        n = numpy.clip(n, self.__slider.minimum(), self.__slider.maximum())
        n = int(n)
        if self.__nintervals != n:
            self.__nintervals = n
            # blocking signals in order to differentiate between
            # changed by user (notified through __on_valueChanged) or
            # changed programmatically (this)
            with blocked(self.__slider):
                self.__slider.setValue(n)
                self.__slabel.setText(str(self.__slider.value()))
            self.changed.emit()

    def setParameters(self, params):
        method = params.get("method", self.EqualFreq)
        nintervals = params.get("n", 5)
        self.setMethod(method)
        if method in [self.EqualFreq, self.EqualWidth]:
            self.setIntervals(nintervals)

    def parameters(self):
        if self.__method in [self.EqualFreq, self.EqualWidth]:
            return {"method": self.__method, "n": self.__nintervals}
        else:
            return {"method": self.__method}

    def __on_buttonClicked(self):
        # on user 'method' button click
        method = self.__group.checkedId()
        if method != self.__method:
            self.setMethod(self.__group.checkedId())
            self.edited.emit()

    def __on_valueChanged(self):
        # on user n intervals slider change.
        self.__nintervals = self.__slider.value()
        self.changed.emit()
        self.edited.emit()
        self.__slabel.setText(str(self.__slider.value()))

    @staticmethod
    def createinstance(params):
        params = dict(params)
        method = params.pop("method", DiscretizeEditor.EqualFreq)
        method, defaults = DiscretizeEditor.Discretizers[method]

        if method is None:
            return None

        resolved = dict(defaults)
        # update only keys in defaults?
        resolved.update(params)
        return preprocess.Discretize(method(**params), remove_const=False)

    def __repr__(self):
        n_int = _tr.m[1254, ", Number of intervals: {}"].format(self.__nintervals) \
            if self.__method in [self.EqualFreq, self.EqualWidth] else ""
        return "{}{}".format(self.Names[self.__method], n_int)


class ContinuizeEditor(BaseEditor):
    _Type = type(Continuize.FirstAsBase)

    Continuizers = OrderedDict([
        (Continuize.FrequentAsBase, _tr.m[1255, "Most frequent is base"]),
        (Continuize.Indicators, _tr.m[1256, "One feature per value"]),
        (Continuize.RemoveMultinomial, _tr.m[1257, "Remove non-binary features"]),
        (Continuize.Remove, _tr.m[1258, "Remove categorical features"]),
        (Continuize.AsOrdinal, _tr.m[1259, "Treat as ordinal"]),
        (Continuize.AsNormalizedOrdinal, _tr.m[1260, "Divide by number of values"])
    ])

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())
        self.__treatment = Continuize.Indicators
        self.__group = group = QButtonGroup(exclusive=True)
        group.buttonClicked.connect(self.__on_buttonClicked)

        for treatment, text in ContinuizeEditor.Continuizers.items():
            rb = QRadioButton(
                text=text,
                checked=self.__treatment == treatment)
            group.addButton(rb, enum_to_index(ContinuizeEditor._Type,
                                              treatment))
            self.layout().addWidget(rb)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def setTreatment(self, treatment):
        buttonid = enum_to_index(ContinuizeEditor._Type, treatment)
        b = self.__group.button(buttonid)
        if b is not None:
            b.setChecked(True)
            self.__treatment = treatment
            self.changed.emit()

    def treatment(self):
        return self.__treatment

    def setParameters(self, params):
        treatment = params.get("multinomial_treatment", Continuize.Indicators)
        self.setTreatment(treatment)

    def parameters(self):
        return {"multinomial_treatment": self.__treatment}

    def __on_buttonClicked(self):
        self.__treatment = index_to_enum(
            ContinuizeEditor._Type, self.__group.checkedId())
        self.changed.emit()
        self.edited.emit()

    @staticmethod
    def createinstance(params):
        params = dict(params)
        treatment = params.pop("multinomial_treatment", Continuize.Indicators)
        return Continuize(multinomial_treatment=treatment)

    def __repr__(self):
        return self.Continuizers[self.__treatment]


class RemoveSparseEditor(BaseEditor):
    options = [_tr.m[1261, "missing values"], _tr.m[1262, "zeros"]]

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.fixedThresh = 50
        self.percThresh = 5
        self.useFixedThreshold = False
        self.filter0 = True
        self.setLayout(QVBoxLayout())

        self.layout().addWidget(QLabel(_tr.m[1263, "Remove features with too many"]))
        self.filter_buttons = QButtonGroup(exclusive=True)
        self.filter_buttons.buttonClicked.connect(self.filterByClicked)
        for idx, option, in enumerate(self.options):
            btn = QRadioButton(self, text=option, checked=idx == 1)
            self.filter_buttons.addButton(btn, id=idx)
            self.layout().addWidget(btn)

        self.layout().addSpacing(20)

        filter_settings = QGroupBox(title=_tr.m[1264, 'Threshold:'], flat=True)
        filter_settings.setLayout(QFormLayout())
        self.settings_buttons = QButtonGroup(exclusive=True)
        self.settings_buttons.buttonClicked.connect(self.filterSettingsClicked)

        btn_perc = QRadioButton(self, text=_tr.m[1265, 'Percentage'], checked=not self.useFixedThreshold)
        self.settings_buttons.addButton(btn_perc, id=0)
        self.percSpin = QSpinBox(minimum=0, maximum=100, value=self.percThresh,
                                 enabled=not self.useFixedThreshold)
        self.percSpin.valueChanged[int].connect(self.setPercThresh)
        self.percSpin.editingFinished.connect(self.edited)

        btn_fix = QRadioButton(self, text=_tr.m[1266, 'Fixed'], checked=self.useFixedThreshold)
        self.settings_buttons.addButton(btn_fix, id=1)
        self.fixedSpin = QSpinBox(minimum=0, maximum=1000000, value=self.fixedThresh,
                                  enabled=self.useFixedThreshold)
        self.fixedSpin.valueChanged[int].connect(self.setFixedThresh)
        self.fixedSpin.editingFinished.connect(self.edited)
        filter_settings.layout().addRow(btn_fix, self.fixedSpin)
        filter_settings.layout().addRow(btn_perc, self.percSpin)

        self.layout().addWidget(filter_settings)

    def filterSettingsClicked(self):
        self.setUseFixedThreshold(self.settings_buttons.checkedId())
        self.percSpin.setEnabled(not self.useFixedThreshold)
        self.fixedSpin.setEnabled(self.useFixedThreshold)
        self.edited.emit()

    def filterByClicked(self):
        self.setFilter0(self.filter_buttons.checkedId())

    def setFilter0(self, id_):
        if self.filter0 != id_:
            self.filter0 = id_
            self.filter_buttons.button(id_).setChecked(True)
            self.edited.emit()

    def setFixedThresh(self, thresh):
        if self.fixedThresh != thresh:
            self.fixedThresh = thresh
            self.fixedSpin.setValue(thresh)
            self.edited.emit()

    def setPercThresh(self, thresh):
        if self.percThresh != thresh:
            self.percThresh = thresh
            self.percSpin.setValue(thresh)
            self.edited.emit()

    def setUseFixedThreshold(self, val):
        if self.useFixedThreshold != val:
            self.useFixedThreshold = val
            self.edited.emit()

    def parameters(self):
        return {'fixedThresh': self.fixedThresh,
                'percThresh' : self.percThresh,
                'useFixedThreshold' : self.useFixedThreshold,
                'filter0' : self.filter0}

    def setParameters(self, params):
        self.setPercThresh(params.get('percThresh', 5))
        self.setFixedThresh(params.get('fixedThresh', 50))
        self.setUseFixedThreshold(params.get('useFixedThreshold', False))
        self.setFilter0(params.get('filter0', True))

    @staticmethod
    def createinstance(params):
        params = dict(params)
        filter0 = params.pop('filter0', True)
        useFixedThreshold = params.pop('useFixedThreshold', False)
        if useFixedThreshold:
            threshold = params.pop('fixedThresh', 50)
        else:
            threshold = params.pop('percThresh', 5) / 100
        return RemoveSparse(threshold, filter0)

    def __repr__(self):
        desc = _tr.e(_tr.c(1267, f"remove features with too many {self.options[self.filter0]}, threshold: "))
        if self.useFixedThreshold:
            desc += _tr.e(_tr.c(1268, f"{self.fixedThresh} {pl(self.fixedThresh, 'instance')}"))
        else:
            desc += f"{self.percThresh} %"
        return desc


class ImputeEditor(BaseEditor):
    (NoImputation, Constant, Average,
     Model, Random, DropRows, DropColumns) = 0, 1, 2, 3, 4, 5, 6

    Imputers = {
        NoImputation: (None, {}),
        #         Constant: (None, {"value": 0})
        Average: (preprocess.impute.Average(), {}),
        #         Model: (preprocess.impute.Model, {}),
        Random: (preprocess.impute.Random(), {}),
        DropRows: (None, {})
    }
    Names = {
        NoImputation: _tr.m[1269, "Don't impute."],
        Constant: _tr.m[1270, "Replace with constant"],
        Average: _tr.m[1271, "Average/Most frequent"],
        Model: _tr.m[1272, "Model based imputer"],
        Random: _tr.m[1273, "Replace with random value"],
        DropRows: _tr.m[1274, "Remove rows with missing values."],
    }

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.__method = ImputeEditor.Average
        self.__group = group = QButtonGroup(self, exclusive=True)
        group.buttonClicked.connect(self.__on_buttonClicked)

        for methodid in [self.Average, self.Random, self.DropRows]:
            text = self.Names[methodid]
            rb = QRadioButton(text=text, checked=self.__method == methodid)
            group.addButton(rb, methodid)
            self.layout().addWidget(rb)

    def setMethod(self, method):
        b = self.__group.button(method)
        if b is not None:
            b.setChecked(True)
            self.__method = method
            self.changed.emit()

    def setParameters(self, params):
        method = params.get("method", ImputeEditor.Average)
        self.setMethod(method)

    def parameters(self):
        return {"method": self.__method}

    def __on_buttonClicked(self):
        self.__method = self.__group.checkedId()
        self.changed.emit()
        self.edited.emit()

    @staticmethod
    def createinstance(params):
        params = dict(params)
        method = params.pop("method", ImputeEditor.Average)
        if method == ImputeEditor.NoImputation:
            return None
        elif method == ImputeEditor.Average:
            return preprocess.Impute()
        elif method == ImputeEditor.Model:
            return preprocess.Impute(method=preprocess.impute.Model())
        elif method == ImputeEditor.DropRows:
            return RemoveNaNRows()
        elif method == ImputeEditor.DropColumns:
            return preprocess.RemoveNaNColumns()
        else:
            method, defaults = ImputeEditor.Imputers[method]
            defaults = dict(defaults)
            defaults.update(params)
            return preprocess.Impute(method=method)

    def __repr__(self):
        return self.Names[self.__method]


class UnivariateFeatureSelect(QWidget):
    changed = Signal()
    edited = Signal()

    #: Strategy
    Fixed, Proportion, FDR, FPR, FWE = 1, 2, 3, 4, 5

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.__scoreidx = 0
        self.__strategy = UnivariateFeatureSelect.Fixed
        self.__k = 10
        self.__p = 75.0

        box = QGroupBox(title=_tr.m[1275, "Score"], flat=True)
        box.setLayout(QVBoxLayout())
        self.__cb = cb = QComboBox(self, )
        self.__cb.currentIndexChanged.connect(self.setScoreIndex)
        self.__cb.activated.connect(self.edited)
        box.layout().addWidget(cb)

        self.layout().addWidget(box)

        box = QGroupBox(title=_tr.m[1276, "Number of features"], flat=True)
        self.__group = group = QButtonGroup(self, exclusive=True)
        self.__spins = {}

        form = QFormLayout()
        fixedrb = QRadioButton(_tr.m[1277, "Fixed:"], checked=True)
        group.addButton(fixedrb, UnivariateFeatureSelect.Fixed)
        kspin = QSpinBox(
            minimum=1, maximum=1000000, value=self.__k,
            enabled=self.__strategy == UnivariateFeatureSelect.Fixed
        )
        kspin.valueChanged[int].connect(self.setK)
        kspin.editingFinished.connect(self.edited)
        self.__spins[UnivariateFeatureSelect.Fixed] = kspin
        form.addRow(fixedrb, kspin)

        percrb = QRadioButton(_tr.m[1278, "Proportion:"])
        group.addButton(percrb, UnivariateFeatureSelect.Proportion)
        pspin = QDoubleSpinBox(
            minimum=1.0, maximum=100.0, singleStep=0.5,
            value=self.__p, suffix="%",
            enabled=self.__strategy == UnivariateFeatureSelect.Proportion
        )

        pspin.valueChanged[float].connect(self.setP)
        pspin.editingFinished.connect(self.edited)
        self.__spins[UnivariateFeatureSelect.Proportion] = pspin
        form.addRow(percrb, pspin)

#         form.addRow(QRadioButton("FDR"), QDoubleSpinBox())
#         form.addRow(QRadioButton("FPR"), QDoubleSpinBox())
#         form.addRow(QRadioButton("FWE"), QDoubleSpinBox())

        self.__group.buttonClicked.connect(self.__on_buttonClicked)
        box.setLayout(form)
        self.layout().addWidget(box)

    def setScoreIndex(self, scoreindex):
        if self.__scoreidx != scoreindex:
            self.__scoreidx = scoreindex
            self.__cb.setCurrentIndex(scoreindex)
            self.changed.emit()

    def scoreIndex(self):
        return self.__scoreidx

    def setStrategy(self, strategy):
        if self.__strategy != strategy:
            self.__strategy = strategy
            b = self.__group.button(strategy)
            b.setChecked(True)
            for st, rb in self.__spins.items():
                rb.setEnabled(st == strategy)
            self.changed.emit()

    def setK(self, k):
        if self.__k != k:
            self.__k = k
            spin = self.__spins[UnivariateFeatureSelect.Fixed]
            spin.setValue(k)
            if self.__strategy == UnivariateFeatureSelect.Fixed:
                self.changed.emit()

    def setP(self, p):
        if self.__p != p:
            self.__p = p
            spin = self.__spins[UnivariateFeatureSelect.Proportion]
            spin.setValue(p)
            if self.__strategy == UnivariateFeatureSelect.Proportion:
                self.changed.emit()

    def setItems(self, itemlist):
        for item in itemlist:
            self.__cb.addItem(item["text"])

    def __on_buttonClicked(self):
        strategy = self.__group.checkedId()
        self.setStrategy(strategy)
        self.edited.emit()

    def setParameters(self, params):
        score = params.get("score", 0)
        strategy = params.get("strategy", UnivariateFeatureSelect.Fixed)
        self.setScoreIndex(score)
        self.setStrategy(strategy)
        if strategy == UnivariateFeatureSelect.Fixed:
            self.setK(params.get("k", 10))
        else:
            self.setP(params.get("p", 75))

    def parameters(self):
        score = self.__scoreidx
        strategy = self.__strategy
        p = self.__p
        k = self.__k

        return {"score": score, "strategy": strategy, "p": p, "k": k}


class FeatureSelectEditor(BaseEditor):

    MEASURES = [
        (_tr.m[1279, "Information Gain"], preprocess.score.InfoGain),
        (_tr.m[1280, "Gain ratio"], preprocess.score.GainRatio),
        (_tr.m[1281, "Gini index"], preprocess.score.Gini),
        ("ReliefF", preprocess.score.ReliefF),
        (_tr.m[1282, "Fast Correlation Based Filter"], preprocess.score.FCBF),
        ("ANOVA", preprocess.score.ANOVA),
        ("Chi2", preprocess.score.Chi2),
        ("RReliefF", preprocess.score.RReliefF),
        (_tr.m[1283, "Univariate Linear Regression"], preprocess.score.UnivariateLinearRegression)
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.__score = 0
        self.__selecionidx = 0

        self.__uni_fs = UnivariateFeatureSelect()
        self.__uni_fs.setItems(
            [{"text": _tr.m[1284, "Information Gain"], "tooltip": ""},
             {"text": _tr.m[1285, "Gain Ratio"]},
             {"text": _tr.m[1286, "Gini Index"]},
             {"text": "ReliefF"},
             {"text": _tr.m[1287, "Fast Correlation Based Filter"]},
             {"text": "ANOVA"},
             {"text": "Chi2"},
             {"text": "RReliefF"},
             {"text": _tr.m[1288, "Univariate Linear Regression"]}
            ]
        )
        self.layout().addWidget(self.__uni_fs)
        self.__uni_fs.changed.connect(self.changed)
        self.__uni_fs.edited.connect(self.edited)

    def setParameters(self, params):
        self.__uni_fs.setParameters(params)

    def parameters(self):
        return self.__uni_fs.parameters()

    @staticmethod
    def createinstance(params):
        params = dict(params)
        score = params.pop("score", 0)
        score = FeatureSelectEditor.MEASURES[score][1]
        strategy = params.get("strategy", UnivariateFeatureSelect.Fixed)
        k = params.get("k", 10)
        p = params.get("p", 75.0)
        if strategy == UnivariateFeatureSelect.Fixed:
            return preprocess.fss.SelectBestFeatures(score(), k=k)
        elif strategy == UnivariateFeatureSelect.Proportion:
            return preprocess.fss.SelectBestFeatures(score(), k=p / 100)
        else:
            raise NotImplementedError

    def __repr__(self):
        params = self.__uni_fs.parameters()
        return _tr.m[1289, "Score: {}, Strategy (Fixed): {}"].format(
            self.MEASURES[params["score"]][0], params["k"])

# TODO: Model based FS (random forest variable importance, ...), RFE
# Unsupervised (min variance, constant, ...)??

class RandomFeatureSelectEditor(BaseEditor):
    #: Strategy
    Fixed, Percentage = 1, 2

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.__strategy = RandomFeatureSelectEditor.Fixed
        self.__k = 10
        self.__p = 75.0

        box = QGroupBox(title=_tr.m[1290, "Number of features"], flat=True)
        self.__group = group = QButtonGroup(self, exclusive=True)
        self.__spins = {}

        form = QFormLayout()
        fixedrb = QRadioButton(_tr.m[1291, "Fixed"], checked=True)
        group.addButton(fixedrb, RandomFeatureSelectEditor.Fixed)
        kspin = QSpinBox(
            minimum=1, maximum=1000000, value=self.__k,
            enabled=self.__strategy == RandomFeatureSelectEditor.Fixed
        )
        kspin.valueChanged[int].connect(self.setK)
        kspin.editingFinished.connect(self.edited)
        self.__spins[RandomFeatureSelectEditor.Fixed] = kspin
        form.addRow(fixedrb, kspin)

        percrb = QRadioButton(_tr.m[1292, "Percentage"])
        group.addButton(percrb, RandomFeatureSelectEditor.Percentage)
        pspin = QDoubleSpinBox(
            minimum=0.0, maximum=100.0, singleStep=0.5,
            value=self.__p, suffix="%",
            enabled=self.__strategy == RandomFeatureSelectEditor.Percentage
        )
        pspin.valueChanged[float].connect(self.setP)
        pspin.editingFinished.connect(self.edited)
        self.__spins[RandomFeatureSelectEditor.Percentage] = pspin
        form.addRow(percrb, pspin)

        self.__group.buttonClicked.connect(self.__on_buttonClicked)
        box.setLayout(form)
        self.layout().addWidget(box)

    def setStrategy(self, strategy):
        if self.__strategy != strategy:
            self.__strategy = strategy
            b = self.__group.button(strategy)
            b.setChecked(True)
            for st, rb in self.__spins.items():
                rb.setEnabled(st == strategy)
            self.changed.emit()

    def setK(self, k):
        if self.__k != k:
            self.__k = k
            spin = self.__spins[RandomFeatureSelectEditor.Fixed]
            spin.setValue(k)
            if self.__strategy == RandomFeatureSelectEditor.Fixed:
                self.changed.emit()

    def setP(self, p):
        if self.__p != p:
            self.__p = p
            spin = self.__spins[RandomFeatureSelectEditor.Percentage]
            spin.setValue(p)
            if self.__strategy == RandomFeatureSelectEditor.Percentage:
                self.changed.emit()

    def __on_buttonClicked(self):
        strategy = self.__group.checkedId()
        self.setStrategy(strategy)
        self.edited.emit()

    def setParameters(self, params):
        strategy = params.get("strategy", RandomFeatureSelectEditor.Fixed)
        self.setStrategy(strategy)
        if strategy == RandomFeatureSelectEditor.Fixed:
            self.setK(params.get("k", 10))
        else:
            self.setP(params.get("p", 75.0))

    def parameters(self):
        strategy = self.__strategy
        p = self.__p
        k = self.__k

        return {"strategy": strategy, "p": p, "k": k}

    @staticmethod
    def createinstance(params):
        params = dict(params)
        strategy = params.get("strategy", RandomFeatureSelectEditor.Fixed)
        k = params.get("k", 10)
        p = params.get("p", 75.0)
        if strategy == RandomFeatureSelectEditor.Fixed:
            return preprocess.fss.SelectRandomFeatures(k=k)
        elif strategy == RandomFeatureSelectEditor.Percentage:
            return preprocess.fss.SelectRandomFeatures(k=p/100)
        else:
            # further implementations
            raise NotImplementedError

    def __repr__(self):
        if self.__strategy == self.Fixed:
            # private attributes may not appear translated strings
            num = self.__k
            return _tr.e(_tr.c(1293, f"select {num} {pl(num,'feature')}"))
        else:
            perc = self.__p
            return _tr.e(_tr.c(1294, f"select {perc} % features"))


def index_to_enum(enum, i):
    """Enums, by default, are not int-comparable, so use an ad-hoc mapping of
    int to enum value at that position"""
    return list(enum)[i]


def enum_to_index(enum, key):
    """Enums, by default, are not int-comparable, so use an ad-hoc mapping of
    enum key to its int position"""
    return list(enum).index(key)

class Scale(BaseEditor):
    CenterByMean, ScaleBySD, NormalizeBySD, NormalizeBySpan_ZeroBased, \
        NormalizeSpan_NonZeroBased = 0, 1, 2, 3, 4

    Names = {
        NormalizeBySD: _tr.m[1295, "Standardize to μ=0, σ²=1"],
        CenterByMean: _tr.m[1296, "Center to μ=0"],
        ScaleBySD: _tr.m[1297, "Scale to σ²=1"],
        NormalizeSpan_NonZeroBased: _tr.m[1298, "Normalize to interval [-1, 1]"],
        NormalizeBySpan_ZeroBased: _tr.m[1299, "Normalize to interval [0, 1]"],
    }

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.__method = Scale.NormalizeBySD
        self.__group = group = QButtonGroup(self, exclusive=True)
        group.buttonClicked.connect(self.__on_buttonClicked)

        for methodid in [self.NormalizeBySD, self.CenterByMean, self.ScaleBySD,
                         self.NormalizeSpan_NonZeroBased,
                         self.NormalizeBySpan_ZeroBased]:
            text = self.Names[methodid]
            rb = QRadioButton(text=text, checked=self.__method == methodid)
            group.addButton(rb, methodid)
            self.layout().addWidget(rb)

    def setMethod(self, method):
        b = self.__group.button(method)
        if b is not None:
            b.setChecked(True)
            self.__method = method
            self.changed.emit()

    def setParameters(self, params):
        method = params.get("method", Scale.NormalizeBySD)
        self.setMethod(method)

    def parameters(self):
        return {"method": self.__method}

    def __on_buttonClicked(self):
        self.__method = self.__group.checkedId()
        self.changed.emit()
        self.edited.emit()

    @staticmethod
    def createinstance(params):
        method = params.get("method", Scale.NormalizeBySD)
        if method == Scale.CenterByMean:
            return _Scale(_Scale.CenteringType.Mean,
                          _Scale.ScalingType.NoScaling)
        elif method == Scale.ScaleBySD:
            return _Scale(_Scale.CenteringType.NoCentering,
                          _Scale.ScalingType.Std)
        elif method == Scale.NormalizeBySD:
            return Normalize(norm_type=Normalize.NormalizeBySD)
        elif method == Scale.NormalizeBySpan_ZeroBased:
            return Normalize(norm_type=Normalize.NormalizeBySpan)
        else:  # method == Scale.NormalizeSpan_NonZeroBased
            return Normalize(norm_type=Normalize.NormalizeBySpan,
                             zero_based=False)

    def __repr__(self):
        return self.Names[self.__method]


class Randomize(BaseEditor):
    RandomizeClasses, RandomizeAttributes, RandomizeMetas = _Randomize.Type

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        form = QFormLayout()
        self.__rand_type_cb = QComboBox()
        self.__rand_type_cb.addItems([_tr.m[1300, "Classes"],
                                      _tr.m[1301, "Features"],
                                      _tr.m[1302, "Meta data"]])

        self.__rand_type_cb.currentIndexChanged.connect(self.changed)
        self.__rand_type_cb.activated.connect(self.edited)

        self.__rand_seed_ch = QCheckBox()
        self.__rand_seed_ch.clicked.connect(self.edited)

        form.addRow(_tr.m[1303, "Randomize:"], self.__rand_type_cb)
        form.addRow(_tr.m[1304, "Replicable shuffling:"], self.__rand_seed_ch)
        self.layout().addLayout(form)

    def setParameters(self, params):
        rand_type = params.get("rand_type", Randomize.RandomizeClasses)
        self.__rand_type_cb.setCurrentIndex(
            enum_to_index(_Randomize.Type, rand_type))
        self.__rand_seed_ch.setChecked(params.get("rand_seed", 1) or 0)

    def parameters(self):
        return {"rand_type": index_to_enum(_Randomize.Type,
                                           self.__rand_type_cb.currentIndex()),
                "rand_seed": 1 if self.__rand_seed_ch.isChecked() else None}

    @staticmethod
    def createinstance(params):
        rand_type = params.get("rand_type", Randomize.RandomizeClasses)
        rand_seed = params.get("rand_seed", 1)
        return _Randomize(rand_type=rand_type, rand_seed=rand_seed)

    def __repr__(self):
        return "{}, {}".format(self.__rand_type_cb.currentText(),
                               _tr.m[1305, "Replicable"] if self.__rand_seed_ch.isChecked()
                               else _tr.m[1306, "Not replicable"])


class PCA(BaseEditor):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.n_components = 10

        form = QFormLayout()
        self.cspin = QSpinBox(minimum=1, value=self.n_components)
        self.cspin.valueChanged[int].connect(self.setC)
        self.cspin.editingFinished.connect(self.edited)

        form.addRow(_tr.m[1307, "Components:"], self.cspin)
        self.layout().addLayout(form)

    def setParameters(self, params):
        self.n_components = params.get("n_components", 10)

    def parameters(self):
        return {"n_components": self.n_components}

    def setC(self, n_components):
        if self.n_components != n_components:
            self.n_components = n_components
            self.cspin.setValue(n_components)
            self.changed.emit()

    @staticmethod
    def createinstance(params):
        n_components = params.get("n_components", 10)
        return ProjectPCA(n_components=n_components)

    def __repr__(self):
        return _tr.m[1308, "Components: {}"].format(self.cspin.value())


class CUR(BaseEditor):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QVBoxLayout())

        self.rank = 10
        self.max_error = 1

        form = QFormLayout()
        self.rspin = QSpinBox(minimum=2, maximum=1000000, value=self.rank)
        self.rspin.valueChanged[int].connect(self.setR)
        self.rspin.editingFinished.connect(self.edited)
        self.espin = QDoubleSpinBox(
            minimum=0.1, maximum=100.0, singleStep=0.1,
            value=self.max_error)
        self.espin.valueChanged[float].connect(self.setE)
        self.espin.editingFinished.connect(self.edited)

        form.addRow(_tr.m[1309, "Rank:"], self.rspin)
        form.addRow(_tr.m[1310, "Relative error:"], self.espin)
        self.layout().addLayout(form)

    def setParameters(self, params):
        self.setR(params.get("rank", 10))
        self.setE(params.get("max_error", 1))

    def parameters(self):
        return {"rank": self.rank, "max_error": self.max_error}

    def setR(self, rank):
        if self.rank != rank:
            self.rank = rank
            self.rspin.setValue(rank)
            self.changed.emit()

    def setE(self, max_error):
        if self.max_error != max_error:
            self.max_error = max_error
            self.espin.setValue(max_error)
            self.changed.emit()

    @staticmethod
    def createinstance(params):
        rank = params.get("rank", 10)
        max_error = params.get("max_error", 1)
        return ProjectCUR(rank=rank, max_error=max_error)

    def __repr__(self):
        return _tr.m[1311, "Rank: {}, Relative error: {}"].format(self.rspin.value(),
                                                     self.espin.value())


# This is intended for future improvements.
# I.e. it should be possible to add/register preprocessor actions
# through entry points (for use by add-ons). Maybe it should be a
# general framework (this is not the only place where such
# functionality is desired (for instance in Orange v2.* Rank widget
# already defines its own entry point).
class Description:
    """
    A description of an action/function.
    """
    def __init__(self, title, icon=None, summary=None, input_=None, output=None,
                 requires=None, note=None, related=None, keywords=None,
                 helptopic=None):
        self.title = title
        self.icon = icon
        self.summary = summary
        self.input = input_
        self.output = output
        self.requires = requires
        self.note = note
        self.related = related
        self.keywords = keywords
        self.helptopic = helptopic


class PreprocessAction:
    def __init__(self, name, qualname, category, description, viewclass):
        self.name = name
        self.qualname = qualname
        self.category = category
        self.description = description
        self.viewclass = viewclass


def icon_path(basename):
    path = importlib.resources.files(__package__).joinpath("icons/" + basename)
    return str(path)


PREPROCESS_ACTIONS = [
    PreprocessAction(
        _tr.m[1312, "Discretize"], "orange.preprocess.discretize", _tr.m[1313, "Discretization"],
        Description(_tr.m[1314, "Discretize Continuous Variables"],
                    icon_path("Discretize.svg")),
        DiscretizeEditor
    ),
    PreprocessAction(
        _tr.m[1315, "Continuize"], "orange.preprocess.continuize", _tr.m[1316, "Continuization"],
        Description(_tr.m[1317, "Continuize Discrete Variables"],
                    icon_path("Continuize.svg")),
        ContinuizeEditor
    ),
    PreprocessAction(
        _tr.m[1318, "Impute"], "orange.preprocess.impute", _tr.m[1319, "Impute"],
        Description(_tr.m[1320, "Impute Missing Values"],
                    icon_path("Impute.svg")),
        ImputeEditor
    ),
    PreprocessAction(
        _tr.m[1321, "Feature Selection"], "orange.preprocess.fss", _tr.m[1322, "Feature Selection"],
        Description(_tr.m[1323, "Select Relevant Features"],
                    icon_path("SelectColumns.svg")),
        FeatureSelectEditor
    ),
    PreprocessAction(
        _tr.m[1324, "Random Feature Selection"], "orange.preprocess.randomfss",
        _tr.m[1325, "Random Feature Selection"],
        Description(_tr.m[1326, "Select Random Features"],
                    icon_path("SelectColumnsRandom.svg")),
        RandomFeatureSelectEditor
    ),
    PreprocessAction(
        _tr.m[1327, "Normalize"], "orange.preprocess.scale", _tr.m[1328, "Scale"],
        Description(_tr.m[1329, "Normalize Features"],
                    icon_path("Normalize.svg")),
        Scale
    ),
    PreprocessAction(
        _tr.m[1330, "Randomize"], "orange.preprocess.randomize", _tr.m[1331, "Randomization"],
        Description(_tr.m[1332, "Randomize"],
                    icon_path("Random.svg")),
        Randomize
    ),
    PreprocessAction(
        _tr.m[1333, "Remove Sparse"], "orange.preprocess.remove_sparse", _tr.m[1334, "Feature Selection"],
        Description(_tr.m[1335, "Remove Sparse Features"],
                    icon_path("PurgeDomain.svg")),
        RemoveSparseEditor
    ),
    PreprocessAction(
        "PCA", "orange.preprocess.pca", "PCA",
        Description(_tr.m[1336, "Principal Component Analysis"],
                    icon_path("PCA.svg")),
        PCA
    ),
    PreprocessAction(
        _tr.m[1337, "CUR"], "orange.preprocess.cur", _tr.m[1338, "CUR"],
        Description(_tr.m[1339, "CUR Matrix Decomposition"],
                    icon_path("SelectColumns.svg")),
        CUR
    )
]


# TODO: Extend with entry points here
# PREPROCESS_ACTIONS += iter_entry_points("Orange.widgets.data.owpreprocess")

# ####
# The actual owwidget
# ####

# Note:
# The preprocessors are drag/dropped onto a sequence widget, where
# they can be reordered/removed/edited.
#
# Model <-> Adapter/Controller <-> View
#
# * `Model`: the current constructed preprocessor model.
# * the source (of drag/drop) is an item model displayed in a list
#   view (source list).
# * the drag/drop is controlled by the controller/adapter,


class OWPreprocess(widget.OWWidget, openclass=True):
    name = _tr.m[1340, "Preprocess"]
    description = _tr.m[1341, "Construct a data preprocessing pipeline."]
    category = _tr.m[1342, "Transform"]
    icon = "icons/Preprocess.svg"
    priority = 2100
    keywords = _tr.m[1343, "preprocess, process"]

    settings_version = 2

    class Inputs:
        data = Input(_tr.m[1344, "Data"], Orange.data.Table)

    class Outputs:
        preprocessor = Output(_tr.m[1345, "Preprocessor"], preprocess.preprocess.Preprocess, dynamic=False)
        preprocessed_data = Output(_tr.m[1346, "Preprocessed Data"], Orange.data.Table)

    storedsettings = Setting({})
    autocommit = Setting(True)
    PREPROCESSORS = PREPROCESS_ACTIONS
    CONTROLLER = Controller

    def __init__(self):
        super().__init__()

        self.data = None
        self._invalidated = False

        # List of available preprocessors (DescriptionRole : Description)
        self.preprocessors = QStandardItemModel()

        def mimeData(indexlist):
            assert len(indexlist) == 1
            index = indexlist[0]
            qname = index.data(DescriptionRole).qualname
            m = QMimeData()
            m.setData("application/x-qwidget-ref", qname.encode("utf-8"))
            return m
        # TODO: Fix this (subclass even if just to pass a function
        # for mimeData delegate)
        self.preprocessors.mimeData = mimeData

        box = gui.vBox(self.controlArea, _tr.m[1347, "Preprocessors"])
        gui.rubber(self.controlArea)

        # we define a class that lets us set the vertical sizeHint
        # based on the height and number of items in the list
        # see self.__update_list_sizeHint

        class ListView(QListView):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.vertical_hint = None

            def sizeHint(self):
                sh = super().sizeHint()
                if self.vertical_hint:
                    return QSize(sh.width(), self.vertical_hint)
                return sh

        self.preprocessorsView = view = ListView(
            selectionMode=QListView.SingleSelection,
            dragEnabled=True,
            dragDropMode=QListView.DragOnly
        )
        view.setModel(self.preprocessors)
        view.activated.connect(self.__activated)

        box.layout().addWidget(view)

        ####
        self._qname2ppdef = {ppdef.qualname: ppdef for
                             ppdef in self.PREPROCESSORS}

        # List of 'selected' preprocessors and their parameters.
        self.preprocessormodel = None

        self.flow_view = SequenceFlow()
        self.controler = self.CONTROLLER(self.flow_view, parent=self)

        self.overlay = OverlayWidget(self)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay.setWidget(self.flow_view)
        self.overlay.setLayout(QVBoxLayout())
        self.overlay.layout().addWidget(
            QLabel(_tr.m[1348, "Drag items from the list on the left"], wordWrap=True))

        self.scroll_area = QScrollArea(
            verticalScrollBarPolicy=Qt.ScrollBarAlwaysOn
        )
        self.scroll_area.viewport().setAcceptDrops(True)
        self.scroll_area.setWidget(self.flow_view)
        self.scroll_area.setWidgetResizable(True)
        self.mainArea.layout().addWidget(self.scroll_area)
        self.flow_view.installEventFilter(self)

        gui.auto_apply(self.buttonsArea, self, "autocommit")

        self.__update_size_constraint_timer = QTimer(
            self, singleShot=True, interval=0,
        )
        self.__update_size_constraint_timer.timeout.connect(self.__update_size_constraint)
        self._initialize()

    def _initialize(self):
        for pp_def in self.PREPROCESSORS:
            description = pp_def.description
            if description.icon:
                icon = QIcon(description.icon)
            else:
                icon = QIcon()
            item = QStandardItem(icon, description.title)
            item.setToolTip(description.summary or "")
            item.setData(pp_def, DescriptionRole)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                          Qt.ItemIsDragEnabled)
            self.preprocessors.appendRow([item])

        self.__update_list_sizeHint()

        model = self.load(self.storedsettings)

        self.set_model(model)

        if not model.rowCount():
            # enforce default width constraint if no preprocessors
            # are instantiated (if the model is not empty the constraints
            # will be triggered by LayoutRequest event on the `flow_view`)
            self.__update_size_constraint()

        self.apply()

    def __update_list_sizeHint(self):
        view = self.preprocessorsView

        h = view.sizeHintForRow(0)
        n = self.preprocessors.rowCount()
        view.vertical_hint = n * h + 2  # only on Mac?
        view.updateGeometry()

    def load(self, saved):
        """Load a preprocessor list from a dict."""
        preprocessors = saved.get("preprocessors", [])
        model = StandardItemModel()

        def dropMimeData(data, action, row, _column, _parent):
            if data.hasFormat("application/x-qwidget-ref") and \
                    action == Qt.CopyAction:
                qname = bytes(data.data("application/x-qwidget-ref")).decode()

                ppdef = self._qname2ppdef[qname]
                item = QStandardItem(ppdef.description.title)
                item.setData({}, ParametersRole)
                item.setData(ppdef.description.title, Qt.DisplayRole)
                item.setData(ppdef, DescriptionRole)
                self.preprocessormodel.insertRow(row, [item])
                return True
            else:
                return False

        model.dropMimeData = dropMimeData

        for qualname, params in preprocessors:
            pp_def = self._qname2ppdef[qualname]
            description = pp_def.description
            item = QStandardItem(description.title)
            if description.icon:
                icon = QIcon(description.icon)
            else:
                icon = QIcon()
            item.setIcon(icon)
            item.setToolTip(description.summary)
            item.setData(pp_def, DescriptionRole)
            item.setData(params, ParametersRole)

            model.appendRow(item)
        return model

    @staticmethod
    def save(model):
        """Save the preprocessor list to a dict."""
        d = {"name": ""}
        preprocessors = []
        for i in range(model.rowCount()):
            item = model.item(i)
            pp_def = item.data(DescriptionRole)
            params = item.data(ParametersRole)
            preprocessors.append((pp_def.qualname, params))

        d["preprocessors"] = preprocessors
        return d


    def set_model(self, ppmodel):
        if self.preprocessormodel:
            self.preprocessormodel.dataChanged.disconnect(self.__on_modelchanged)
            self.preprocessormodel.rowsInserted.disconnect(self.__on_modelchanged)
            self.preprocessormodel.rowsRemoved.disconnect(self.__on_modelchanged)
            self.preprocessormodel.rowsMoved.disconnect(self.__on_modelchanged)
            self.preprocessormodel.deleteLater()

        self.preprocessormodel = ppmodel
        self.controler.setModel(ppmodel)
        if ppmodel is not None:
            self.preprocessormodel.dataChanged.connect(self.__on_modelchanged)
            self.preprocessormodel.rowsInserted.connect(self.__on_modelchanged)
            self.preprocessormodel.rowsRemoved.connect(self.__on_modelchanged)
            self.preprocessormodel.rowsMoved.connect(self.__on_modelchanged)

        self.__update_overlay()

    def __update_overlay(self):
        if self.preprocessormodel is None or \
                self.preprocessormodel.rowCount() == 0:
            self.overlay.setWidget(self.flow_view)
            self.overlay.show()
        else:
            self.overlay.setWidget(None)
            self.overlay.hide()

    def __on_modelchanged(self):
        self.__update_overlay()
        self.commit.deferred()

    @Inputs.data
    @check_sql_input
    def set_data(self, data=None):
        """Set the input dataset."""
        self.data = data

    def handleNewSignals(self):
        self.apply()

    def __activated(self, index):
        item = self.preprocessors.itemFromIndex(index)
        action = item.data(DescriptionRole)
        item = QStandardItem()
        item.setData({}, ParametersRole)
        item.setData(action.description.title, Qt.DisplayRole)
        item.setData(action, DescriptionRole)
        self.preprocessormodel.appendRow([item])

    def buildpreproc(self):
        plist = []
        for i in range(self.preprocessormodel.rowCount()):
            item = self.preprocessormodel.item(i)
            desc = item.data(DescriptionRole)
            params = item.data(ParametersRole)

            if not isinstance(params, dict):
                params = {}

            create = desc.viewclass.createinstance
            plist.append(create(params))

        if len(plist) == 1:
            return plist[0]
        else:
            return preprocess.preprocess.PreprocessorList(plist)

    def apply(self):
        # Sync the model into storedsettings on every apply.
        self.storeSpecificSettings()
        preprocessor = self.buildpreproc()

        if self.data is not None:
            self.error()
            try:
                data = preprocessor(self.data)
            except (ValueError, ZeroDivisionError) as e:
                self.error(str(e))
                return
        else:
            data = None

        self.Outputs.preprocessor.send(preprocessor)
        self.Outputs.preprocessed_data.send(data)

    @gui.deferred
    def commit(self):
        if not self._invalidated:
            self._invalidated = True
            QApplication.postEvent(self, QEvent(QEvent.User))

    def customEvent(self, event):
        if event.type() == QEvent.User and self._invalidated:
            self._invalidated = False
            self.apply()

    def eventFilter(self, receiver, event):
        if receiver is self.flow_view and event.type() == QEvent.LayoutRequest:
            self.__update_size_constraint_timer.start()
        return super().eventFilter(receiver, event)

    def storeSpecificSettings(self):
        """Reimplemented."""
        self.storedsettings = self.save(self.preprocessormodel)
        super().storeSpecificSettings()

    def saveSettings(self):
        """Reimplemented."""
        self.storedsettings = self.save(self.preprocessormodel)
        super().saveSettings()

    @classmethod
    def migrate_settings(cls, settings, version):
        if version < 2:
            for action, params in settings["storedsettings"]["preprocessors"]:
                if action == "orange.preprocess.scale":
                    scale = center = None
                    if "center" in params:
                        center = params.pop("center").name
                    if "scale" in params:
                        scale = params.pop("scale").name
                    migratable = {
                        ("Mean", "NoScaling"): Scale.CenterByMean,
                        ("NoCentering", "Std"): Scale.ScaleBySD,
                        ("Mean", "Std"): Scale.NormalizeBySD,
                        ("NoCentering", "Span"): Scale.NormalizeBySpan_ZeroBased
                    }
                    params["method"] = \
                        migratable.get((center, scale), Scale.NormalizeBySD)

    def onDeleteWidget(self):
        self.data = None
        self.set_model(None)
        super().onDeleteWidget()

    @Slot()
    def __update_size_constraint(self):
        # Update minimum width constraint on the scroll area containing
        # the 'instantiated' preprocessor list (to avoid the horizontal
        # scroll bar).
        sh = self.flow_view.minimumSizeHint()
        scroll_width = self.scroll_area.verticalScrollBar().width()
        self.scroll_area.setMinimumWidth(
            min(max(sh.width() + scroll_width + 2, self.controlArea.width()),
                520))

    def send_report(self):
        pp = [(self.controler.model().index(i, 0).data(Qt.DisplayRole), w)
              for i, w in enumerate(self.controler.view.widgets())]
        if pp:
            self.report_items(_tr.m[1349, "Settings"], pp)

if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWPreprocess).run(Orange.data.Table("brown-selected"))

```

## widgets/utils/owlearnerwidget.py

```python
from orangecanvas.localization.si import plsi, plsi_sz, z_besedo
from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator
from copy import deepcopy

from AnyQt.QtCore import QTimer, Qt

from Orange.data import Table
from Orange.modelling import Fitter, Learner, Model
from Orange.preprocess.preprocess import Preprocess
from Orange.statistics import util as ut
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils import getmembers
from Orange.widgets.utils.signals import Output, Input
from Orange.widgets.utils.sql import check_sql_input
from Orange.widgets.widget import OWWidget, WidgetMetaClass, Msg


class OWBaseLearnerMeta(WidgetMetaClass):
    """ Meta class for learner widgets

    OWBaseLearner declares two outputs, learner and model with
    generic type (Learner and Model).

    This metaclass ensures that each of the subclasses gets
    its own Outputs class with output that match the corresponding
    learner.
    """
    def __new__(cls, name, bases, attributes, **kwargs):
        def abstract_widget():
            return not attributes.get("name")

        def copy_outputs(template):
            result = type("Outputs", (), {})
            for name, signal in getmembers(template, Output):
                setattr(result, name, deepcopy(signal))
            return result

        obj = super().__new__(cls, name, bases, attributes, **kwargs)
        if abstract_widget():
            return obj

        learner = attributes.get("LEARNER")
        if not learner:
            raise AttributeError(
                "'{}' must declare attribute LEARNER".format(name))

        outputs = obj.Outputs = copy_outputs(obj.Outputs)
        outputs.learner.type = learner
        outputs.model.type = learner.__returns__

        return obj


class OWBaseLearner(OWWidget, metaclass=OWBaseLearnerMeta, openclass=True):
    """Abstract widget for classification/regression learners.

    Notes
    -----
    All learner widgets should define learner class LEARNER.
    LEARNER should have __returns__ attribute.

    Overwrite `create_learner`, `add_main_layout` and `get_learner_parameters`
    in case LEARNER has extra parameters.

    """
    LEARNER = None
    supports_sparse = True

    learner_name = Setting("", schema_only=True)
    want_main_area = False
    resizing_enabled = False
    auto_apply = Setting(True)

    class Error(OWWidget.Error):
        data_error = Msg("{}")
        fitting_failed = Msg(_tr.m[3271, "Fitting failed.\n{}"])
        sparse_not_supported = Msg(_tr.m[3272, "Sparse data is not supported."])
        out_of_memory = Msg(_tr.m[3273, "Out of memory."])

    class Warning(OWWidget.Warning):
        outdated_learner = Msg(_tr.m[3274, "Press Apply to submit changes."])

    class Information(OWWidget.Information):
        ignored_preprocessors = Msg(
            (_tr.m[3275, "Ignoring default preprocessing.\n"] + (_tr.m[3276, "Default preprocessing, such as scaling, one-hot encoding and "] + (_tr.m[3277, "treatment of missing data, has been replaced with user-specified "] + (_tr.m[3278, "preprocessors. Problems may occur if these are inadequate "] + _tr.m[3279, "for the given data."])))))

    class Inputs:
        data = Input(_tr.m[3280, "Data"], Table)
        preprocessor = Input(_tr.m[3281, "Preprocessor"], Preprocess)

    class Outputs:
        learner = Output(_tr.m[3282, "Learner"], Learner, dynamic=False)
        model = Output(_tr.m[3283, "Model"], Model, dynamic=False,
                       replaces=[_tr.m[3284, "Classifier"], _tr.m[3285, "Predictor"]])

    OUTPUT_MODEL_NAME = Outputs.model.name  # Attr for backcompat w/ self.send() code

    _SEND, _SOFT, _UPDATE = range(3)

    def __init__(self, preprocessors=None):
        super().__init__()
        self.__default_learner_name = ""
        self.data = None
        self.valid_data = False
        self.learner = None
        self.model = None
        self.preprocessors = preprocessors
        self.outdated_settings = False
        self.__apply_level = []

        self.setup_layout()
        QTimer.singleShot(0, getattr(self, "unconditional_apply", self.apply))

    def create_learner(self):
        """Creates a learner with current configuration.

        Returns:
            Learner: an instance of Orange.base.learner subclass.
        """
        return self.LEARNER(preprocessors=self.preprocessors)

    def get_learner_parameters(self):
        """Creates an `OrderedDict` or a sequence of pairs with current model
        configuration.

        Returns:
            OrderedDict or List: (option, value) pairs or dict
        """
        return []

    def default_learner_name(self) -> str:
        """
        Return the default learner name.

        By default this is the same as the widget's name.
        """
        return self.__default_learner_name or self.captionTitle

    def set_default_learner_name(self, name: str) -> None:
        """
        Set the default learner name if not otherwise specified by the user.
        """
        changed = name != self.__default_learner_name
        if name:
            self.name_line_edit.setPlaceholderText(name)
        else:
            self.name_line_edit.setPlaceholderText(self.captionTitle)
        self.__default_learner_name = name
        if not self.learner_name and changed:
            self.learner_name_changed()

    @Inputs.preprocessor
    def set_preprocessor(self, preprocessor):
        self.preprocessors = preprocessor
        # invalidate learner and model, so handleNewSignals will renew them
        self.learner = self.model = None

    @Inputs.data
    @check_sql_input
    def set_data(self, data):
        """Set the input train dataset."""
        self.Error.data_error.clear()
        self.data = data

        if data is not None and data.domain.class_var is None:
            if data.domain.class_vars:
                self.Error.data_error(
                    (_tr.m[3286, "Data contains multiple target variables.\n"] + _tr.m[3287, "Select a single one with the Select Columns widget."]))
            else:
                self.Error.data_error(
                    (_tr.m[3288, "Data has no target variable.\n"] + _tr.m[3289, "Select one with the Select Columns widget."]))
            self.data = None

        # invalidate the model so that handleNewSignals will update it
        self.model = None


    def apply(self):
        level, self.__apply_level = max(self.__apply_level, default=self._UPDATE), []
        """Applies learner and sends new model."""
        if level == self._SEND:
            self._send_learner()
            self._send_model()
        elif level == self._UPDATE:
            self.update_learner()
            self.update_model()
        else:
            self.learner or self.update_learner()
            self.model or self.update_model()

    def apply_as(self, level, unconditional=False):
        self.__apply_level.append(level)
        if unconditional:
            self.unconditional_apply()
        else:
            self.apply()

    def update_learner(self):
        self.learner = self.create_learner()
        if self.learner and issubclass(self.LEARNER, Fitter):
            self.learner.use_default_preprocessors = True
        if self.learner is not None:
            self.learner.name = self.effective_learner_name()
        self._send_learner()

    def _send_learner(self):
        self.Outputs.learner.send(self.learner)
        self.outdated_settings = False
        self.Warning.outdated_learner.clear()

    def handleNewSignals(self):
        self.apply_as(self._SOFT, True)
        self.Information.ignored_preprocessors(
            shown=not getattr(self.learner, "use_default_preprocessors", False)
                  and getattr(self.LEARNER, "preprocessors", False)
                  and self.preprocessors is not None)

    def show_fitting_failed(self, exc):
        """Show error when fitting fails.
            Derived widgets can override this to show more specific messages."""
        self.Error.fitting_failed(str(exc), shown=exc is not None)

    def update_model(self):
        self.show_fitting_failed(None)
        self.model = None
        if self.check_data():
            try:
                self.model = self.learner(self.data)
            except BaseException as exc:
                self.show_fitting_failed(exc)
            else:
                self.model.name = self.effective_learner_name()
                self.model.instances = self.data
        self._send_model()

    def _send_model(self):
        self.Outputs.model.send(self.model)

    def check_data(self):
        self.valid_data = False
        self.Error.sparse_not_supported.clear()
        if self.data is not None and self.learner is not None:
            self.Error.data_error.clear()

            reason = self.learner.incompatibility_reason(self.data.domain)
            if reason is not None:
                self.Error.data_error(reason)
            elif not len(self.data):
                self.Error.data_error(_tr.m[3290, "Dataset is empty."])
            elif len(ut.unique(self.data.Y)) < 2:
                self.Error.data_error(_tr.m[3291, "Data contains a single target value."])
            elif self.data.X.size == 0:
                self.Error.data_error(_tr.m[3292, "Data has no features to learn from."])
            elif self.data.is_sparse() and not self.supports_sparse:
                self.Error.sparse_not_supported()
            else:
                self.valid_data = True

        return self.valid_data

    def settings_changed(self, *args, **kwargs):
        self.outdated_settings = True
        self.Warning.outdated_learner(shown=not self.auto_apply)
        self.apply()

    def learner_name_changed(self):
        if self.model is not None:
            self.model.name = self.effective_learner_name()
        if self.learner is not None:
            self.learner.name = self.effective_learner_name()
        self.apply_as(self._SEND)

    def effective_learner_name(self):
        """Return the effective learner name."""
        return self.learner_name or self.name_line_edit.placeholderText()

    def send_report(self):
        self.report_items(((_tr.m[3293, "Name"], self.effective_learner_name()),))

        model_parameters = self.get_learner_parameters()
        if model_parameters:
            self.report_items(_tr.m[3294, "Model parameters"], model_parameters)

        if self.data:
            self.report_data(_tr.m[3295, "Data"], self.data)

    # GUI
    def setup_layout(self):
        self.add_learner_name_widget()
        self.add_main_layout()
        # Options specific to target variable type, if supported
        if issubclass(self.LEARNER, Fitter):
            # Only add a classification section if the method is overridden
            if type(self).add_classification_layout is not \
                    OWBaseLearner.add_classification_layout:
                classification_box = gui.widgetBox(
                    self.controlArea, _tr.m[3296, 'Classification'])
                self.add_classification_layout(classification_box)
            # Only add a regression section if the method is overridden
            if type(self).add_regression_layout is not \
                    OWBaseLearner.add_regression_layout:
                regression_box = gui.widgetBox(self.controlArea, _tr.m[3297, 'Regression'])
                self.add_regression_layout(regression_box)
        self.add_bottom_buttons()

    def add_main_layout(self):
        """Creates layout with the learner configuration widgets.

        Override this method for laying out any learner-specific parameter controls.
        See setup_layout() method for execution order.
        """

    def add_classification_layout(self, box):
        """Creates layout for classification specific options.

        If a widget outputs a learner dispatcher, sometimes the classification
        and regression learners require different options.
        See `setup_layout()` method for execution order.
        """

    def add_regression_layout(self, box):
        """Creates layout for regression specific options.

        If a widget outputs a learner dispatcher, sometimes the classification
        and regression learners require different options.
        See `setup_layout()` method for execution order.
        """

    def add_learner_name_widget(self):
        self.name_line_edit = gui.lineEdit(
            self.controlArea, self, 'learner_name', box=_tr.m[3298, 'Name'],
            placeholderText=self.captionTitle,
            tooltip=_tr.m[3299, 'The name will identify this model in other widgets'],
            orientation=Qt.Horizontal, callback=self.learner_name_changed)

    def setCaption(self, caption):
        super().setCaption(caption)
        if not self.__default_learner_name:
            self.name_line_edit.setPlaceholderText(caption)
            if not self.learner_name:
                self.learner_name_changed()

    def add_bottom_buttons(self):
        self.apply_button = gui.auto_apply(self.buttonsArea, self, commit=self.apply)

    def send(self, signalName, value, id=None):
        # A subclass might still use the old syntax to send outputs
        # defined on this class
        for _, output in getmembers(self.Outputs, Output):
            if output.name == signalName or signalName in output.replaces:
                output.send(value, id=id)
                return

        super().send(signalName, value, id)

    @classmethod
    def get_widget_description(cls):
        # When a subclass defines defines old-style signals, those override
        # the new-style ones, so we add them manually
        desc = super().get_widget_description()

        if cls.outputs:
            desc["outputs"].extend(cls.get_signals("outputs", True))
        if cls.inputs:
            desc["inputs"].extend(cls.get_signals("inputs", True))
        return desc

```
