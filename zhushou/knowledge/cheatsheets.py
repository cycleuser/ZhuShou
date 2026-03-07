"""Built-in concise API cheatsheets for common Python frameworks.

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

CHEATSHEETS["torch"] = """\
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


def get_cheatsheet(name: str) -> str | None:
    """Return the cheatsheet for *name*, or ``None`` if not available."""
    return CHEATSHEETS.get(name)


def list_cheatsheets() -> list[str]:
    """Return sorted list of available cheatsheet names."""
    return sorted(CHEATSHEETS)
