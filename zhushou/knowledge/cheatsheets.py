"""Built-in concise API cheatsheets for common frameworks and tools.

Each cheatsheet is a compact markdown string covering core imports,
key classes/functions with signatures, and minimal usage examples.
Designed to fit within small-model context windows (~500-2000 chars each).
"""

from __future__ import annotations

CHEATSHEETS: dict[str, str] = {}

# ── NumPy ─────────────────────────────────────────────────────────────

CHEATSHEETS["numpy"] = """\
## NumPy Quick Reference
import numpy as np

### Array Creation
np.array(object, dtype=None) -> ndarray
np.zeros(shape, dtype=float) -> ndarray
np.ones(shape, dtype=float) -> ndarray
np.empty(shape, dtype=float) -> ndarray
np.arange(start, stop=None, step=1) -> ndarray
np.linspace(start, stop, num=50) -> ndarray
np.eye(N) -> ndarray  # identity matrix
np.random.rand(d0, d1, ...) -> ndarray  # uniform [0,1)
np.random.randn(d0, d1, ...) -> ndarray  # standard normal

### Attributes
arr.shape, arr.dtype, arr.ndim, arr.size, arr.T

### Reshaping
arr.reshape(new_shape) -> ndarray
arr.flatten() -> ndarray
arr.ravel() -> ndarray
np.concatenate([a, b], axis=0)
np.stack([a, b], axis=0)
np.split(arr, indices_or_sections, axis=0)

### Indexing & Slicing
arr[start:stop:step]        # basic slicing
arr[condition]               # boolean indexing
arr[[0, 2, 4]]              # fancy indexing
np.where(condition, x, y)   # conditional selection

### Math Operations
np.add(a, b), np.subtract(a, b), np.multiply(a, b), np.divide(a, b)
np.dot(a, b), a @ b         # matrix multiply
np.sum(a, axis=None), np.mean(a, axis=None)
np.std(a, axis=None), np.var(a, axis=None)
np.min(a, axis=None), np.max(a, axis=None)
np.argmin(a), np.argmax(a)
np.sort(a, axis=-1), np.argsort(a)

### Linear Algebra
np.linalg.inv(a)            # inverse
np.linalg.det(a)            # determinant
np.linalg.eig(a)            # eigenvalues & vectors
np.linalg.solve(a, b)       # solve Ax = b
np.linalg.norm(a)           # vector/matrix norm

### Example
a = np.array([[1, 2], [3, 4]])
b = np.linalg.inv(a)
print(a @ b)  # identity matrix
"""

# ── Pandas ────────────────────────────────────────────────────────────

CHEATSHEETS["pandas"] = """\
## Pandas Quick Reference
import pandas as pd

### Data Structures
pd.Series(data, index=None, name=None)
pd.DataFrame(data, index=None, columns=None)

### I/O
pd.read_csv(path, sep=',', header=0, index_col=None, dtype=None) -> DataFrame
pd.read_excel(path, sheet_name=0) -> DataFrame
pd.read_json(path) -> DataFrame
df.to_csv(path, index=True), df.to_excel(path), df.to_json(path)

### Inspection
df.head(n=5), df.tail(n=5), df.info(), df.describe()
df.shape, df.columns, df.dtypes, df.index
df.isnull().sum(), df.nunique()

### Selection
df['col'], df[['col1', 'col2']]         # column(s)
df.loc[row_label, col_label]             # label-based
df.iloc[row_idx, col_idx]               # integer-based
df.query("col > 5")                      # string query
df[df['col'] > 5]                        # boolean mask

### Manipulation
df.drop(columns=['col']), df.rename(columns={'old': 'new'})
df.sort_values('col', ascending=True)
df.groupby('col').agg({'val': ['mean', 'sum']})
df.merge(other, on='key', how='inner')   # join
pd.concat([df1, df2], axis=0)            # stack
df.pivot_table(values='val', index='row', columns='col', aggfunc='mean')
df.apply(func, axis=0)                   # apply function
df.fillna(value), df.dropna()

### Example
df = pd.DataFrame({'name': ['A', 'B', 'C'], 'score': [90, 80, 70]})
print(df.groupby('name')['score'].mean())
"""

# ── Matplotlib ────────────────────────────────────────────────────────

CHEATSHEETS["matplotlib"] = """\
## Matplotlib Quick Reference
import matplotlib.pyplot as plt
import numpy as np

### Figure & Axes
fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8, 6))
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

### Basic Plots
ax.plot(x, y, fmt='b-', label='line')      # line plot
ax.scatter(x, y, c=colors, s=sizes)        # scatter
ax.bar(x, height, width=0.8)               # bar chart
ax.barh(y, width)                           # horizontal bar
ax.hist(data, bins=30, edgecolor='black')   # histogram
ax.pie(sizes, labels=labels, autopct='%1.1f%%')
ax.imshow(image, cmap='gray')              # image display
ax.contour(X, Y, Z), ax.contourf(X, Y, Z) # contour

### Customization
ax.set_title('Title'), ax.set_xlabel('X'), ax.set_ylabel('Y')
ax.set_xlim(lo, hi), ax.set_ylim(lo, hi)
ax.legend(loc='best')
ax.grid(True, linestyle='--', alpha=0.7)
ax.set_xticks(ticks), ax.set_xticklabels(labels, rotation=45)

### Saving & Display
plt.tight_layout()
plt.savefig('plot.png', dpi=150, bbox_inches='tight')
plt.show()
plt.close(fig)

### Example
x = np.linspace(0, 2 * np.pi, 100)
fig, ax = plt.subplots()
ax.plot(x, np.sin(x), label='sin')
ax.plot(x, np.cos(x), label='cos')
ax.legend()
plt.savefig('trig.png')
"""

# ── SciPy ─────────────────────────────────────────────────────────────

CHEATSHEETS["scipy"] = """\
## SciPy Quick Reference
import numpy as np

### Optimization (scipy.optimize)
from scipy.optimize import minimize, curve_fit, root
result = minimize(fun, x0, method='Nelder-Mead')  # result.x, result.fun
popt, pcov = curve_fit(model_func, xdata, ydata)   # fit parameters
sol = root(equations_func, x0)                      # solve f(x)=0

### Interpolation (scipy.interpolate)
from scipy.interpolate import interp1d, CubicSpline
f = interp1d(x, y, kind='linear')       # 'linear', 'cubic', 'quadratic'
cs = CubicSpline(x, y)
y_new = f(x_new)

### Linear Algebra (scipy.linalg)
from scipy.linalg import solve, inv, det, eig, svd, lu
x = solve(A, b)                          # solve Ax = b
U, s, Vt = svd(A)

### Integration (scipy.integrate)
from scipy.integrate import quad, dblquad, solve_ivp
result, error = quad(func, a, b)          # definite integral
sol = solve_ivp(ode_func, t_span, y0)    # ODE solver

### Signal Processing (scipy.signal)
from scipy.signal import butter, filtfilt, find_peaks
b, a = butter(N=4, Wn=0.1, btype='low')
filtered = filtfilt(b, a, data)
peaks, props = find_peaks(data, height=0.5)

### Statistics (scipy.stats)
from scipy.stats import norm, ttest_ind, pearsonr
p_value = norm.cdf(x, loc=0, scale=1)
stat, pval = ttest_ind(sample1, sample2)
r, p = pearsonr(x, y)

### FFT (scipy.fft)
from scipy.fft import fft, ifft, fftfreq
yf = fft(signal)
xf = fftfreq(n, d=1/sample_rate)

### Example
from scipy.optimize import minimize
result = minimize(lambda x: (x[0]-1)**2 + (x[1]-2)**2, [0, 0])
print(result.x)  # [1.0, 2.0]
"""

# ── SymPy ─────────────────────────────────────────────────────────────

CHEATSHEETS["sympy"] = """\
## SymPy Quick Reference
from sympy import symbols, Symbol, Eq, solve, simplify, expand, factor
from sympy import sin, cos, tan, exp, log, sqrt, pi, oo, I

### Symbol Declaration
x, y, z = symbols('x y z')
n = Symbol('n', integer=True, positive=True)

### Expression Manipulation
expand((x + 1)**2)         # x**2 + 2*x + 1
factor(x**2 - 1)           # (x - 1)*(x + 1)
simplify(sin(x)**2 + cos(x)**2)  # 1
expr.subs(x, 2)            # substitute value
expr.subs([(x, 1), (y, 2)])

### Solving Equations
solve(x**2 - 4, x)                # [-2, 2]
solve([x + y - 3, x - y - 1], [x, y])  # {x: 2, y: 1}
solve(Eq(x**2, 4), x)

### Calculus
from sympy import diff, integrate, limit, series, summation
diff(sin(x), x)                   # cos(x)
diff(x**3, x, 2)                  # 6*x (2nd derivative)
integrate(x**2, x)                # x**3/3
integrate(x**2, (x, 0, 1))       # 1/3 (definite)
limit(sin(x)/x, x, 0)            # 1
series(exp(x), x, 0, n=5)        # Taylor series

### Linear Algebra
from sympy import Matrix
M = Matrix([[1, 2], [3, 4]])
M.det(), M.inv(), M.eigenvals(), M.eigenvects()
M.rref()  # row reduced echelon form

### Printing
from sympy import pprint, latex
pprint(expr)                       # pretty terminal output
latex(expr)                        # LaTeX string

### Example
x = symbols('x')
expr = x**3 - 6*x**2 + 11*x - 6
roots = solve(expr, x)            # [1, 2, 3]
print(factor(expr))               # (x - 1)*(x - 2)*(x - 3)
"""

# ── PyTorch ───────────────────────────────────────────────────────────

CHEATSHEETS["pytorch"] = """\
## PyTorch Quick Reference
import torch
import torch.nn as nn
import torch.optim as optim

### Tensor Creation
torch.tensor(data, dtype=None) -> Tensor
torch.zeros(size), torch.ones(size), torch.empty(size)
torch.rand(size), torch.randn(size)   # uniform / normal
torch.arange(start, end, step)
torch.linspace(start, end, steps)
tensor.to(device)                      # 'cpu' or 'cuda'

### Tensor Operations
tensor.shape, tensor.dtype, tensor.device
tensor.reshape(shape), tensor.view(shape)
tensor.unsqueeze(dim), tensor.squeeze(dim)
torch.cat([a, b], dim=0), torch.stack([a, b], dim=0)
tensor.item()                          # scalar to Python number

### Autograd
tensor = torch.tensor([1.0], requires_grad=True)
loss.backward()                        # compute gradients
tensor.grad                            # access gradient
with torch.no_grad():                  # disable grad tracking

### Neural Network Modules
class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(in_features, out_features)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(out_features, num_classes)
    def forward(self, x):
        return self.fc2(self.relu(self.fc1(x)))

### Common Layers
nn.Linear(in, out), nn.Conv2d(in_ch, out_ch, kernel)
nn.BatchNorm1d(features), nn.Dropout(p=0.5)
nn.ReLU(), nn.Sigmoid(), nn.Softmax(dim=1)
nn.CrossEntropyLoss(), nn.MSELoss()

### Training Loop Pattern
model = MyModel()
optimizer = optim.Adam(model.parameters(), lr=1e-3)
for epoch in range(num_epochs):
    optimizer.zero_grad()
    output = model(input_data)
    loss = criterion(output, target)
    loss.backward()
    optimizer.step()

### Save / Load
torch.save(model.state_dict(), 'model.pth')
model.load_state_dict(torch.load('model.pth'))
"""

# Backward-compat alias
CHEATSHEETS["torch"] = CHEATSHEETS["pytorch"]

# ── PySide6 ───────────────────────────────────────────────────────────

CHEATSHEETS["pyside6"] = """\
## PySide6 Quick Reference
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QMenuBar, QMenu, QStatusBar, QToolBar,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QAction, QFont, QIcon

### Application & Window
app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle('Title')
window.resize(800, 600)
central = QWidget()
window.setCentralWidget(central)
window.show()
sys.exit(app.exec())

### Layouts
layout = QVBoxLayout()           # vertical
layout = QHBoxLayout()           # horizontal
layout.addWidget(widget)
layout.addLayout(sub_layout)
widget.setLayout(layout)

### Common Widgets
label = QLabel('text')
btn = QPushButton('Click')
btn.clicked.connect(handler)
line = QLineEdit(placeholderText='Enter...')
text = line.text()
combo = QComboBox()
combo.addItems(['A', 'B', 'C'])
combo.currentTextChanged.connect(handler)

### Signals & Slots
class MyWidget(QWidget):
    my_signal = Signal(str)
    @Slot()
    def on_click(self):
        self.my_signal.emit('data')

### Dialogs
path, _ = QFileDialog.getOpenFileName(self, 'Open', '', 'Files (*.*)')
QMessageBox.information(self, 'Title', 'Message')
reply = QMessageBox.question(self, 'Confirm', 'Sure?')

### Menu Bar
menubar = window.menuBar()
file_menu = menubar.addMenu('&File')
action = QAction('&Open', window)
action.setShortcut('Ctrl+O')
action.triggered.connect(handler)
file_menu.addAction(action)

### Timer
timer = QTimer()
timer.timeout.connect(update_func)
timer.start(1000)  # ms

### Example
app = QApplication(sys.argv)
w = QMainWindow()
btn = QPushButton('Hello')
btn.clicked.connect(lambda: print('clicked'))
w.setCentralWidget(btn)
w.show()
sys.exit(app.exec())
"""

# ── PyQtGraph ─────────────────────────────────────────────────────────

CHEATSHEETS["pyqtgraph"] = """\
## PyQtGraph Quick Reference
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np

### Quick Plot (standalone)
pg.plot(x, y, pen='r', symbol='o', title='Plot')
pg.image(np.random.rand(100, 100))

### PlotWidget (embed in Qt)
plot_widget = pg.PlotWidget(title='My Plot')
plot_widget.setLabel('left', 'Y Axis')
plot_widget.setLabel('bottom', 'X Axis')
plot_widget.addLegend()

### Plot Data
curve = plot_widget.plot(x, y, pen=pg.mkPen('r', width=2), name='line1')
scatter = pg.ScatterPlotItem(x, y, size=10, brush='b')
plot_widget.addItem(scatter)
curve.setData(new_x, new_y)           # update data

### Pen & Brush
pen = pg.mkPen(color='r', width=2, style=Qt.DashLine)
brush = pg.mkBrush(color=(255, 0, 0, 128))

### ImageView
imv = pg.ImageView()
imv.setImage(data_2d_or_3d)

### Real-time Update Pattern
timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)  # 20 FPS
def update():
    curve.setData(new_x, new_y)

### GraphicsLayoutWidget (multiple plots)
win = pg.GraphicsLayoutWidget(title='Multi')
p1 = win.addPlot(row=0, col=0, title='Plot 1')
p2 = win.addPlot(row=0, col=1, title='Plot 2')
p1.plot(x, y1)
p2.plot(x, y2)

### Axis & Grid
plot_widget.showGrid(x=True, y=True, alpha=0.3)
plot_widget.setXRange(0, 10)
plot_widget.setYRange(-1, 1)

### Example
app = QtWidgets.QApplication([])
win = pg.PlotWidget(title='Sine Wave')
x = np.linspace(0, 4*np.pi, 200)
win.plot(x, np.sin(x), pen='g')
win.show()
app.exec()
"""

# ── Flask ─────────────────────────────────────────────────────────────

CHEATSHEETS["flask"] = """\
## Flask Quick Reference
from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, abort, session, Blueprint, g,
)

### App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'
app.config['DEBUG'] = True

### Routes
@app.route('/')
def index():
    return 'Hello World'

@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    if request.method == 'POST':
        data = request.get_json()           # JSON body
        return jsonify(result=data), 201
    args = request.args                      # query params
    return jsonify(items=[])

@app.route('/user/<int:user_id>')
def get_user(user_id):
    return jsonify(id=user_id)

### Request Object
request.method                               # 'GET', 'POST', etc.
request.args.get('key', default)             # query string
request.form.get('key')                      # form data
request.get_json()                           # JSON body
request.files['file']                        # uploaded file
request.headers.get('Authorization')

### Response
return jsonify(data), 200                    # JSON response
return render_template('page.html', var=val) # template
return redirect(url_for('index'))            # redirect
abort(404)                                   # error

### Blueprints
bp = Blueprint('api', __name__, url_prefix='/api')
@bp.route('/items')
def list_items():
    return jsonify(items=[])
app.register_blueprint(bp)

### Error Handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify(error='Not found'), 404

### Context & Hooks
@app.before_request
def before():
    g.db = connect_db()

@app.teardown_appcontext
def teardown(exc):
    db = g.pop('db', None)
    if db: db.close()

### Running
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
"""

# ── Scikit-learn ──────────────────────────────────────────────────────

CHEATSHEETS["sklearn"] = """\
## Scikit-learn Quick Reference
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error

### Data Splitting
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

### Preprocessing
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

### Common Estimators
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.cluster import KMeans, DBSCAN

### Fit / Predict / Score API
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
score = model.score(X_test, y_test)           # accuracy or R2

### Cross-Validation
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')

### Hyperparameter Tuning
grid = GridSearchCV(model, param_grid={'n_estimators': [50, 100]}, cv=5)
grid.fit(X_train, y_train)
print(grid.best_params_, grid.best_score_)

### Pipeline
pipe = Pipeline([('scaler', StandardScaler()), ('clf', SVC())])
pipe.fit(X_train, y_train)

### Example
from sklearn.datasets import load_iris
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
clf = RandomForestClassifier().fit(X_train, y_train)
print(clf.score(X_test, y_test))
"""

# ── Scikit-image ──────────────────────────────────────────────────────

CHEATSHEETS["skimage"] = """\
## Scikit-image Quick Reference
import skimage
from skimage import io, color, filters, transform, feature, segmentation, morphology

### I/O
img = io.imread('image.png')              # -> ndarray (H, W, C)
io.imsave('out.png', img)
io.imshow(img); io.show()

### Color Conversion
gray = color.rgb2gray(img)                # -> float64 [0, 1]
hsv = color.rgb2hsv(img)

### Filters
blurred = filters.gaussian(gray, sigma=1.0)
edges = filters.sobel(gray)
thresh = filters.threshold_otsu(gray)
binary = gray > thresh

### Transform
resized = transform.resize(img, (256, 256))
rotated = transform.rotate(img, angle=45)
scaled = transform.rescale(img, 0.5)

### Feature Detection
edges = feature.canny(gray, sigma=1.0)
blobs = feature.blob_log(gray, max_sigma=30)
corners = feature.corner_harris(gray)

### Segmentation
labels = segmentation.slic(img, n_segments=100)
ws = segmentation.watershed(-edges, markers)
boundaries = segmentation.mark_boundaries(img, labels)

### Morphology
dilated = morphology.dilation(binary, morphology.disk(3))
eroded = morphology.erosion(binary, morphology.disk(3))
opened = morphology.opening(binary)
closed = morphology.closing(binary)

### Example
from skimage import data
img = data.coins()
thresh = filters.threshold_otsu(img)
binary = img > thresh
"""

# ── ChemPy ────────────────────────────────────────────────────────────

CHEATSHEETS["chempy"] = """\
## ChemPy Quick Reference
from chempy import Substance, Reaction, Equilibrium
from chempy import balance_stoichiometry

### Substance
water = Substance.from_formula('H2O')
print(water.mass)                         # molar mass

### Balance Equations
reac, prod = balance_stoichiometry({'H2', 'O2'}, {'H2O'})
# reac = {'H2': 2, 'O2': 1}, prod = {'H2O': 2}

### Reactions
rxn = Reaction({'H2': 2, 'O2': 1}, {'H2O': 2})
print(rxn)

### Equilibrium
eq = Equilibrium({'H2': 2, 'O2': 1}, {'H2O': 2}, param=1e5)

### ODE System (kinetics)
from chempy.kinetics.ode import get_odesys
odesys, extra = get_odesys(rsys)
result = odesys.integrate(t_eval, initial_concs)

### Units
from chempy.units import to_unitless, SI_base_registry
conc = 0.1 * SI_base_registry['mol'] / SI_base_registry['dm3']

### Example
reac, prod = balance_stoichiometry({'Fe', 'O2'}, {'Fe2O3'})
print(dict(reac), '->', dict(prod))
"""

# ── Jupyter ───────────────────────────────────────────────────────────

CHEATSHEETS["jupyter"] = """\
## Jupyter Quick Reference

### Magic Commands (IPython)
%timeit expr                              # benchmark single line
%%timeit                                  # benchmark cell
%matplotlib inline                        # inline plots
%run script.py                            # run external script
%load_ext autoreload; %autoreload 2       # auto-reload modules
%env VAR=value                            # set environment variable
%%capture output                          # capture cell output
%who, %whos                               # list variables
%history -n                               # show history with numbers

### Display
from IPython.display import display, HTML, Markdown, Image, Audio, Video
display(HTML('<b>bold</b>'))
display(Markdown('## heading'))
display(Image('plot.png'))

### Widgets (ipywidgets)
import ipywidgets as widgets
slider = widgets.IntSlider(value=5, min=0, max=10, description='N:')
widgets.interact(func, n=slider)

### Notebook API (nbformat)
import nbformat
nb = nbformat.read('notebook.ipynb', as_version=4)
nb.cells[0].source                        # cell content
nbformat.write(nb, 'out.ipynb')

### Shell Commands
!pip install package
!ls -la
result = !grep -r "pattern" .             # capture output

### Example
%%timeit
sum(range(10000))
"""

# ── TensorFlow ────────────────────────────────────────────────────────

CHEATSHEETS["tensorflow"] = """\
## TensorFlow Quick Reference
import tensorflow as tf

### Tensors
tf.constant([1, 2, 3])
tf.Variable(initial_value)
tf.zeros(shape), tf.ones(shape), tf.random.normal(shape)
tf.cast(tensor, tf.float32)

### tf.function (graph mode)
@tf.function
def compute(x):
    return x ** 2 + 2 * x + 1

### Keras Sequential API
model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation='relu', input_shape=(784,)),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10, activation='softmax'),
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(X_train, y_train, epochs=10, validation_split=0.2)
model.evaluate(X_test, y_test)
y_pred = model.predict(X_new)

### Common Layers
tf.keras.layers.Dense(units, activation)
tf.keras.layers.Conv2D(filters, kernel_size, activation)
tf.keras.layers.LSTM(units, return_sequences=False)
tf.keras.layers.BatchNormalization()
tf.keras.layers.Flatten()

### tf.data.Dataset
ds = tf.data.Dataset.from_tensor_slices((X, y))
ds = ds.shuffle(1000).batch(32).prefetch(tf.data.AUTOTUNE)

### Custom Training
with tf.GradientTape() as tape:
    logits = model(x, training=True)
    loss = loss_fn(y, logits)
grads = tape.gradient(loss, model.trainable_variables)
optimizer.apply_gradients(zip(grads, model.trainable_variables))

### Save / Load
model.save('model.keras')
loaded = tf.keras.models.load_model('model.keras')
"""

# ── CUDA / PyCUDA ─────────────────────────────────────────────────────

CHEATSHEETS["cuda"] = """\
## CUDA/PyCUDA Quick Reference
import pycuda.autoinit
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np

### GPU Arrays
a_gpu = gpuarray.to_gpu(np.array([1, 2, 3], dtype=np.float32))
result = (a_gpu * 2).get()                # transfer back to CPU

### Custom Kernel
mod = SourceModule(\"\"\"
__global__ void multiply(float *a, float *b, float *c, int n) {
    int idx = threadIdx.x + blockIdx.x * blockDim.x;
    if (idx < n) c[idx] = a[idx] * b[idx];
}
\"\"\")
func = mod.get_function("multiply")
func(a_gpu, b_gpu, c_gpu, np.int32(n), block=(256,1,1), grid=(n//256+1,1))

### Memory Management
a_gpu = drv.mem_alloc(a.nbytes)           # allocate
drv.memcpy_htod(a_gpu, a)                 # host -> device
drv.memcpy_dtoh(a, a_gpu)                 # device -> host

### Device Info
dev = drv.Device(0)
print(dev.name(), dev.total_memory())
print(dev.compute_capability())

### Example
a = np.random.randn(1000).astype(np.float32)
a_gpu = gpuarray.to_gpu(a)
print((a_gpu ** 2).get().sum())
"""

# ── OpenCL / PyOpenCL ─────────────────────────────────────────────────

CHEATSHEETS["opencl"] = """\
## OpenCL/PyOpenCL Quick Reference
import pyopencl as cl
import numpy as np

### Context & Queue
ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

### Buffers
mf = cl.mem_flags
a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
c_buf = cl.Buffer(ctx, mf.WRITE_ONLY, a.nbytes)

### Kernel Program
prg = cl.Program(ctx, \"\"\"
__kernel void add(__global const float *a, __global const float *b,
                  __global float *c) {
    int gid = get_global_id(0);
    c[gid] = a[gid] + b[gid];
}
\"\"\").build()
prg.add(queue, a.shape, None, a_buf, b_buf, c_buf)

### Read Back
c = np.empty_like(a)
cl.enqueue_copy(queue, c, c_buf)

### Device Info
for platform in cl.get_platforms():
    for device in platform.get_devices():
        print(device.name, device.global_mem_size)

### Example
a = np.random.rand(1000).astype(np.float32)
b = np.random.rand(1000).astype(np.float32)
# ... create buffers, run kernel, read result
"""

# ── Rust ──────────────────────────────────────────────────────────────

CHEATSHEETS["rust"] = """\
## Rust Quick Reference

### Variables & Types
let x: i32 = 5;                           // immutable
let mut y = 10;                            // mutable
let s: String = String::from("hello");
let slice: &str = "hello";

### Ownership & Borrowing
let s1 = String::from("hi");
let s2 = s1;                               // s1 moved, no longer valid
fn borrow(s: &String) {}                   // immutable borrow
fn mutate(s: &mut String) {}               // mutable borrow

### Structs & Enums
struct Point { x: f64, y: f64 }
enum Option<T> { Some(T), None }
impl Point {
    fn distance(&self) -> f64 { (self.x*self.x + self.y*self.y).sqrt() }
}

### Pattern Matching
match value {
    1 => println!("one"),
    2..=5 => println!("2-5"),
    _ => println!("other"),
}

### Error Handling
fn read_file(path: &str) -> Result<String, io::Error> {
    let content = fs::read_to_string(path)?;   // ? propagates error
    Ok(content)
}

### Collections
let v: Vec<i32> = vec![1, 2, 3];
let mut map = HashMap::new();
map.insert("key", "value");

### Traits
trait Summary { fn summarize(&self) -> String; }
impl Summary for Article { fn summarize(&self) -> String { ... } }

### Cargo
cargo new project_name
cargo build / cargo run / cargo test
cargo add serde                            // add dependency
"""

# ── JavaScript ────────────────────────────────────────────────────────

CHEATSHEETS["javascript"] = """\
## JavaScript Quick Reference

### Variables
let x = 10;                               // block-scoped, reassignable
const y = 20;                              // block-scoped, constant
var z = 30;                                // function-scoped (avoid)

### Functions
function add(a, b) { return a + b; }
const add = (a, b) => a + b;              // arrow function
const greet = (name = 'World') => `Hello ${name}`;

### Destructuring & Spread
const { a, b } = obj;                     // object destructuring
const [first, ...rest] = arr;             // array destructuring
const merged = { ...obj1, ...obj2 };      // spread

### Array Methods
arr.map(x => x * 2)
arr.filter(x => x > 0)
arr.reduce((acc, x) => acc + x, 0)
arr.find(x => x.id === 1)
arr.forEach(x => console.log(x))
arr.some(x => x > 5), arr.every(x => x > 0)

### Promises & Async/Await
fetch(url).then(r => r.json()).then(data => console.log(data));
async function getData() {
    const res = await fetch(url);
    return await res.json();
}

### DOM
document.getElementById('id')
document.querySelector('.class')
el.addEventListener('click', handler)
el.textContent = 'text'
el.classList.add('active')

### Modules
import { func } from './module.js';
export function func() {}
export default class MyClass {}

### Example
const nums = [1, 2, 3, 4, 5];
const evens = nums.filter(n => n % 2 === 0);
console.log(evens);  // [2, 4]
"""

# ── TypeScript ────────────────────────────────────────────────────────

CHEATSHEETS["typescript"] = """\
## TypeScript Quick Reference

### Type Annotations
let name: string = 'Alice';
let age: number = 30;
let items: string[] = ['a', 'b'];
let tuple: [string, number] = ['a', 1];

### Interfaces & Types
interface User { name: string; age: number; email?: string; }
type ID = string | number;                 // union type
type Point = { x: number; y: number };

### Generics
function identity<T>(arg: T): T { return arg; }
interface Box<T> { value: T; }

### Type Guards
function isString(x: unknown): x is string { return typeof x === 'string'; }

### Utility Types
Partial<T>                                 // all fields optional
Required<T>                                // all fields required
Pick<T, 'key1' | 'key2'>                  // subset of fields
Omit<T, 'key'>                            // exclude fields
Record<string, number>                     // { [key: string]: number }
Readonly<T>

### Enums
enum Direction { Up, Down, Left, Right }
enum Color { Red = 'RED', Blue = 'BLUE' }

### Type Assertions
const el = document.getElementById('id') as HTMLInputElement;
const value = <string>someVar;

### Classes
class Animal {
    constructor(public name: string, private age: number) {}
    greet(): string { return `I'm ${this.name}`; }
}

### Example
interface Todo { id: number; title: string; done: boolean; }
const todos: Todo[] = [{ id: 1, title: 'Learn TS', done: false }];
const pending = todos.filter(t => !t.done);
"""

# ── C Language ────────────────────────────────────────────────────────

CHEATSHEETS["c_lang"] = """\
## C Language Quick Reference

### Program Structure
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char *argv[]) { return 0; }

### Types & Variables
int, long, float, double, char, void
unsigned int, size_t, int32_t (stdint.h)
const int MAX = 100;
typedef struct { int x; int y; } Point;

### Pointers & Arrays
int *p = &x;                               // pointer to x
*p = 42;                                   // dereference
int arr[10];                               // stack array
int *buf = malloc(n * sizeof(int));        // heap allocation
free(buf);

### Strings (string.h)
strlen(s), strcmp(s1, s2), strcpy(dst, src)
strcat(dst, src), strncpy(dst, src, n)
sprintf(buf, "fmt %d", val)

### I/O (stdio.h)
printf("fmt %d %s\\n", num, str);
scanf("%d", &num);
FILE *f = fopen("file.txt", "r");
fgets(buf, sizeof(buf), f);
fprintf(f, "data\\n");
fclose(f);

### Control Flow
if (cond) {} else if (cond) {} else {}
for (int i = 0; i < n; i++) {}
while (cond) {}
switch (val) { case 1: break; default: break; }

### Preprocessor
#define MAX(a,b) ((a)>(b)?(a):(b))
#ifdef DEBUG ... #endif

### Compilation
gcc -Wall -O2 -o prog main.c
gcc -c main.c -o main.o && gcc main.o -o prog
"""

# ── C++ ───────────────────────────────────────────────────────────────

CHEATSHEETS["cpp"] = """\
## C++ Quick Reference

### Containers (STL)
#include <vector>
#include <map>
#include <string>
#include <unordered_map>
#include <set>
std::vector<int> v = {1, 2, 3};
v.push_back(4); v.size(); v[0];
std::map<std::string, int> m; m["key"] = 1;
std::unordered_map<std::string, int> um;
std::set<int> s = {3, 1, 2};              // sorted unique

### Smart Pointers
#include <memory>
auto p = std::make_unique<MyClass>(args);  // exclusive ownership
auto sp = std::make_shared<MyClass>(args); // shared ownership
std::weak_ptr<MyClass> wp = sp;

### Classes
class Animal {
public:
    Animal(std::string name) : name_(std::move(name)) {}
    virtual ~Animal() = default;
    virtual void speak() const = 0;        // pure virtual
private:
    std::string name_;
};

### Templates
template<typename T>
T max_val(T a, T b) { return (a > b) ? a : b; }

### Lambdas
auto add = [](int a, int b) { return a + b; };
auto capture = [&x, y](int z) { return x + y + z; };

### Move Semantics
std::string s1 = "hello";
std::string s2 = std::move(s1);            // s1 is now empty

### Range-based For
for (const auto& item : container) { ... }
for (auto& [key, val] : map) { ... }      // structured binding

### Example
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    std::vector<int> v = {3, 1, 4, 1, 5};
    std::sort(v.begin(), v.end());
    for (int x : v) std::cout << x << ' ';
}
"""

# ── Go / Golang ───────────────────────────────────────────────────────

CHEATSHEETS["go"] = """\
## Go Quick Reference

### Package & Main
package main
import "fmt"
func main() { fmt.Println("Hello") }

### Variables & Types
var x int = 10
y := 20                                    // short declaration
const Pi = 3.14
// int, float64, string, bool, byte, rune

### Functions
func add(a, b int) int { return a + b }
func divide(a, b float64) (float64, error) {
    if b == 0 { return 0, fmt.Errorf("division by zero") }
    return a / b, nil
}

### Structs & Methods
type Point struct { X, Y float64 }
func (p Point) Distance() float64 { return math.Sqrt(p.X*p.X + p.Y*p.Y) }

### Interfaces
type Shape interface { Area() float64 }

### Slices & Maps
s := []int{1, 2, 3}
s = append(s, 4)
m := map[string]int{"a": 1, "b": 2}
val, ok := m["key"]

### Goroutines & Channels
go func() { fmt.Println("async") }()
ch := make(chan int)
go func() { ch <- 42 }()
val := <-ch

### Select
select {
case msg := <-ch1: handle(msg)
case ch2 <- val: // sent
default: // non-blocking
}

### Error Handling
if err != nil { return fmt.Errorf("wrap: %w", err) }

### Defer
defer file.Close()

### Testing
// file: math_test.go
func TestAdd(t *testing.T) {
    if add(2, 3) != 5 { t.Error("expected 5") }
}
// go test ./...
"""

# ── HTML / CSS ────────────────────────────────────────────────────────

CHEATSHEETS["html_css"] = """\
## HTML/CSS Quick Reference

### HTML Semantic Elements
<header>, <nav>, <main>, <article>, <section>, <aside>, <footer>
<h1>-<h6>, <p>, <a href="">, <img src="" alt="">
<ul><li>, <ol><li>, <table><tr><td>
<form>, <input>, <textarea>, <select><option>, <button>
<div>, <span>

### Form Elements
<input type="text|password|email|number|checkbox|radio|file|submit">
<input placeholder="..." required>
<select><option value="v">Label</option></select>
<textarea rows="4" cols="50"></textarea>

### CSS Selectors
element, .class, #id
parent child, parent > direct-child
el:hover, el:focus, el:nth-child(2n)
el::before, el::after
[attr="value"]

### Flexbox
.container { display: flex; flex-direction: row; justify-content: center;
             align-items: center; gap: 10px; flex-wrap: wrap; }
.item { flex: 1; }

### Grid
.grid { display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 16px; }
.span2 { grid-column: span 2; }

### Box Model
margin, border, padding, content
box-sizing: border-box;

### Positioning
position: static | relative | absolute | fixed | sticky;
top, right, bottom, left, z-index

### Media Queries
@media (max-width: 768px) { .sidebar { display: none; } }

### Custom Properties
:root { --primary: #007bff; }
.btn { color: var(--primary); }
"""

# ── Bash ──────────────────────────────────────────────────────────────

CHEATSHEETS["bash"] = """\
## Bash Quick Reference

### Variables
name="value"                               # no spaces around =
echo "$name" / echo "${name}_suffix"
readonly CONST="immutable"
export PATH="$PATH:/new/path"

### Conditionals
if [ "$x" -eq 5 ]; then echo "five"; elif [ "$x" -gt 5 ]; then echo ">5"; else echo "<5"; fi
[ -f file ] / [ -d dir ] / [ -e path ]    # file/dir/exists tests
[ -z "$str" ] / [ -n "$str" ]             # empty / non-empty
[[ "$str" == pattern* ]]                   # glob matching

### Loops
for i in 1 2 3; do echo $i; done
for f in *.txt; do echo "$f"; done
for ((i=0; i<10; i++)); do echo $i; done
while read -r line; do echo "$line"; done < file.txt

### Functions
greet() { echo "Hello, $1"; return 0; }
greet "World"

### String Operations
${#str}                                    # length
${str:0:5}                                 # substring
${str/old/new}                             # replace first
${str//old/new}                            # replace all
${str%.ext}                                # remove suffix

### Arrays
arr=(a b c); echo ${arr[1]}               # b
arr+=(d); echo ${#arr[@]}                  # length
for item in "${arr[@]}"; do echo "$item"; done

### Redirection & Pipes
cmd > out.txt 2>&1                         # stdout + stderr
cmd1 | cmd2 | cmd3                         # pipeline
cmd << 'EOF'                               # heredoc
"""

# ── Zsh ───────────────────────────────────────────────────────────────

CHEATSHEETS["zsh"] = """\
## Zsh Quick Reference

### Oh-My-Zsh
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
# Config: ~/.zshrc
plugins=(git docker kubectl zsh-autosuggestions zsh-syntax-highlighting)
ZSH_THEME="robbyrussell"

### Zsh-specific Features
setopt AUTO_CD                             # cd by typing dir name
setopt CORRECT                             # spell correction
setopt EXTENDED_GLOB                       # advanced globbing

### Glob Qualifiers
ls *(.)                                    # regular files only
ls *(/)                                    # directories only
ls *(.om[1,5])                             # 5 newest files
ls **/*.py                                 # recursive glob

### Parameter Expansion
${(U)var}                                  # uppercase
${(L)var}                                  # lowercase
${(s:/:)PATH}                              # split by /

### History
fc -l                                      # list history
!! / !$ / !^                               # last cmd / last arg / first arg
Ctrl+R                                     # reverse search

### Completion
autoload -Uz compinit; compinit
zstyle ':completion:*' menu select         # menu completion

### Key Bindings
bindkey -e                                 # emacs mode
bindkey '^[[A' history-search-backward

### Aliases
alias -g L='| less'                        # global alias
alias -s py=python3                        # suffix alias
"""

# ── PowerShell ────────────────────────────────────────────────────────

CHEATSHEETS["powershell"] = """\
## PowerShell Quick Reference

### Cmdlet Convention: Verb-Noun
Get-Help cmdlet -Full
Get-Command *-Service*
Get-Member -InputObject $obj

### Variables & Types
$name = "Alice"
[int]$count = 0
$arr = @(1, 2, 3)
$hash = @{ key = "value"; num = 42 }

### Pipeline
Get-Process | Where-Object { $_.CPU -gt 100 } | Sort-Object CPU -Descending
Get-ChildItem *.log | ForEach-Object { $_.Length }
Get-Service | Select-Object Name, Status

### Common Cmdlets
Get-ChildItem (ls/dir), Set-Location (cd), Copy-Item (cp)
Remove-Item (rm), New-Item, Move-Item (mv)
Get-Content (cat), Set-Content, Add-Content
Invoke-WebRequest, Invoke-RestMethod
Test-Path, Resolve-Path

### Control Flow
if ($x -gt 5) { } elseif ($x -eq 5) { } else { }
foreach ($item in $collection) { }
1..10 | ForEach-Object { $_ * 2 }
switch ($val) { "a" { } "b" { } default { } }

### Functions
function Get-Greeting { param([string]$Name = "World") "Hello, $Name" }

### Modules
Import-Module ModuleName
Install-Module -Name ModuleName -Scope CurrentUser
Get-Module -ListAvailable

### Example
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 Name, WorkingSet
"""

# ── Fish Shell ────────────────────────────────────────────────────────

CHEATSHEETS["fish"] = """\
## Fish Shell Quick Reference

### Variables
set name "value"                           # local
set -gx PATH $PATH /new/path              # global export
set -e name                                # erase

### Functions
function greet
    echo "Hello, $argv[1]"
end
funcsave greet                             # persist

### Conditionals
if test -f file.txt
    echo "exists"
else if test -d dir
    echo "is dir"
end

### Loops
for f in *.txt
    echo $f
end
while read -l line
    echo $line
end

### String Command
string match -r '\\d+' "abc123"            # regex match
string replace old new $str
string split ',' "a,b,c"
string length $str
string trim $str

### Abbreviations
abbr -a gc 'git commit'
abbr -a gp 'git push'

### Configuration
fish_config                                # web-based config
set fish_greeting ""                       # disable greeting
funced function_name                       # edit function

### Completions
complete -c mycmd -s h -l help -d "Show help"
complete -c mycmd -a "(ls)" -d "Files"

### Event Handlers
function on_pwd --on-variable PWD
    echo "Changed to $PWD"
end

### Example
for f in *.log
    if test (wc -l < $f) -gt 100
        echo "$f has >100 lines"
    end
end
"""

# ── Linux Commands ────────────────────────────────────────────────────

CHEATSHEETS["linux_commands"] = """\
## Linux Commands Quick Reference

### File Operations
ls -la, cp src dst, mv old new, rm -rf dir
mkdir -p path/to/dir, rmdir dir
chmod 755 file, chown user:group file
ln -s target link                          # symbolic link
find . -name "*.py" -type f
find . -mtime -7                           # modified last 7 days

### Text Processing
grep -rn "pattern" dir                     # recursive with line numbers
grep -i -E "regex" file                    # case-insensitive regex
sed 's/old/new/g' file                     # substitute
awk '{print $1, $3}' file                  # print columns
sort file | uniq -c                        # count unique lines
cut -d',' -f1,3 file.csv                   # extract CSV columns
wc -l file                                 # line count
tr 'a-z' 'A-Z' < file                     # translate chars
head -n 20 file, tail -f file             # first/last/follow

### System Info
ps aux, top, htop
df -h, du -sh dir                          # disk usage
free -h                                    # memory
uname -a                                   # kernel info
uptime, who, w

### Network
curl -X GET url, curl -d '{"key":"val"}' -H "Content-Type: application/json" url
wget url -O output
ssh user@host, scp file user@host:path
netstat -tlnp, ss -tlnp                   # open ports
ping host, traceroute host

### Compression
tar czf archive.tar.gz dir                # create
tar xzf archive.tar.gz                    # extract
zip -r archive.zip dir, unzip archive.zip

### Package Management
apt update && apt install pkg              # Debian/Ubuntu
yum install pkg / dnf install pkg          # RHEL/Fedora
"""

# ── Git ───────────────────────────────────────────────────────────────

CHEATSHEETS["git"] = """\
## Git Quick Reference

### Setup
git init, git clone url
git config --global user.name "Name"
git config --global user.email "email"

### Basic Workflow
git status                                 # working tree status
git add file, git add .                    # stage changes
git commit -m "message"                    # commit staged
git push origin branch                     # push to remote
git pull origin branch                     # fetch + merge

### Branching
git branch                                 # list branches
git branch new-branch                      # create branch
git checkout branch, git switch branch     # switch
git checkout -b new-branch                 # create + switch
git merge branch                           # merge into current
git branch -d branch                       # delete branch

### History & Diff
git log --oneline --graph
git log --author="name" --since="2024-01-01"
git diff                                   # unstaged changes
git diff --staged                          # staged changes
git show commit_hash

### Undo & Reset
git restore file                           # discard changes
git restore --staged file                  # unstage
git reset --soft HEAD~1                    # undo commit, keep staged
git reset --hard HEAD~1                    # undo commit + changes
git revert commit_hash                     # create undo commit

### Stash
git stash, git stash pop
git stash list, git stash drop

### Remote
git remote -v
git remote add origin url
git fetch origin
git push -u origin branch                  # set upstream

### Tags
git tag v1.0.0
git push --tags
"""

# ── Docker ────────────────────────────────────────────────────────────

CHEATSHEETS["docker"] = """\
## Docker Quick Reference

### Images
docker build -t name:tag .
docker images, docker rmi image
docker pull image:tag, docker push image:tag
docker tag source:tag target:tag

### Containers
docker run -d -p 8080:80 --name myapp image
docker run -it --rm image /bin/bash        # interactive
docker ps, docker ps -a                    # running / all
docker stop name, docker start name
docker rm name, docker rm -f name
docker logs -f name                        # follow logs
docker exec -it name /bin/bash             # shell into container

### Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
ENTRYPOINT ["python"]                      # fixed command

### Volumes & Networks
docker volume create vol
docker run -v vol:/data image
docker run -v $(pwd):/app image            # bind mount
docker network create net
docker run --network net image

### Docker Compose
docker compose up -d                       # start services
docker compose down                        # stop + remove
docker compose logs -f service
docker compose build
docker compose ps

### Cleanup
docker system prune                        # remove unused
docker image prune -a
docker volume prune
"""

# ── kubectl / Kubernetes ──────────────────────────────────────────────

CHEATSHEETS["kubectl"] = """\
## kubectl Quick Reference

### Cluster Info
kubectl cluster-info
kubectl get nodes
kubectl config get-contexts
kubectl config use-context ctx-name

### Resources
kubectl get pods, kubectl get pods -A      # all namespaces
kubectl get deployments, kubectl get services
kubectl get configmaps, kubectl get secrets
kubectl get all -n namespace

### Inspect
kubectl describe pod pod-name
kubectl logs pod-name [-c container] [-f]
kubectl top pods, kubectl top nodes

### Create / Apply / Delete
kubectl apply -f manifest.yaml
kubectl create deployment name --image=img
kubectl delete -f manifest.yaml
kubectl delete pod pod-name

### Scale & Rollout
kubectl scale deployment name --replicas=3
kubectl rollout status deployment name
kubectl rollout undo deployment name
kubectl rollout history deployment name

### Exec & Port-Forward
kubectl exec -it pod-name -- /bin/bash
kubectl port-forward pod-name 8080:80
kubectl port-forward svc/service 8080:80

### Namespace
kubectl create namespace ns
kubectl get pods -n ns
kubectl config set-context --current --namespace=ns

### ConfigMap & Secret
kubectl create configmap name --from-file=config.yaml
kubectl create secret generic name --from-literal=key=value

### Example
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl scale deployment nginx --replicas=3
"""


def get_cheatsheet(name: str) -> str | None:
    """Return the cheatsheet for *name*, or ``None`` if not available."""
    return CHEATSHEETS.get(name)


def list_cheatsheets() -> list[str]:
    """Return sorted list of available cheatsheet names."""
    return sorted(CHEATSHEETS)
