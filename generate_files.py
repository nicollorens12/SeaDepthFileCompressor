from InputFileGenerator import InputFileGenerator

# Configuración para generar exactamente 849 líneas
LINE_LENGTH = 35001
NUM_LINES = 849
TOTAL_VALUES = LINE_LENGTH * NUM_LINES

gen = InputFileGenerator(line_length=LINE_LENGTH)
gen.generate_random_walk('files/rw.txt', N=TOTAL_VALUES, sigma=2.0)
gen.generate_noise('files/noise.txt', N=TOTAL_VALUES, low=0, high=8000)
gen.generate_periodic('files/periodic.txt', N=TOTAL_VALUES, amplitude=1500, periods=10, offset=6000)
gen.generate_mixed('files/mixed.txt', N=TOTAL_VALUES)

print(f"Archivos generados con {NUM_LINES} líneas y {LINE_LENGTH} valores por línea")
print(f"Total de valores por archivo: {TOTAL_VALUES:,}")