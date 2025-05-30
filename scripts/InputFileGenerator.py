import numpy as np

class InputFileGenerator:
    """
    Genera ficheros de alturas sintéticas con la misma estructura (múltiples líneas, valores separados por espacios).
    """
    def __init__(self, line_length=1000):
        # Número máximo de valores por línea
        self.line_length = line_length

    def _write_heights(self, heights, file_path):
        with open(file_path, 'w') as f:
            for i in range(0, len(heights), self.line_length):
                chunk = heights[i:i+self.line_length]
                f.write(' '.join(str(int(h)) for h in chunk) + '\n')

    def generate_random_walk(self, file_path, N, sigma=1.0, start=0):
        """
        Genera una caminata aleatoria:
          h_i = h_{i-1} + Normal(0, sigma)
        """
        deltas = np.random.normal(loc=0.0, scale=sigma, size=N)
        heights = np.cumsum(deltas).astype(int) + start
        self._write_heights(heights, file_path)

    def generate_noise(self, file_path, N, low=0, high=10000):
        """
        Genera ruido puro uniforme en [low, high].
        """
        heights = np.random.randint(low=low, high=high+1, size=N)
        self._write_heights(heights, file_path)

    def generate_periodic(self, file_path, N, amplitude=2000, periods=5, offset=5000):
        """
        Genera un patrón sinusoidal:
          h_i = amplitude * sin(2π * periods * i / N) + offset
        """
        x = np.linspace(0, 2 * np.pi * periods, N)
        heights = (amplitude * np.sin(x) + offset).astype(int)
        self._write_heights(heights, file_path)

    def generate_mixed(self, file_path, N):
        """
        Combina tres segmentos: random_walk, ruido puro y periódico.
        Cada segmento ocupa aproximadamente N/3
        """
        n1 = N // 3
        n2 = N // 3
        n3 = N - n1 - n2
        # Segmentos
        deltas1 = np.random.normal(scale=1.0, size=n1)
        heights1 = np.cumsum(deltas1).astype(int)
        heights2 = np.random.randint(0, 10000, size=n2)
        x = np.linspace(0, 2 * np.pi * 3, n3)
        heights3 = (2000 * np.sin(x) + 5000).astype(int)
        # Concatenar y escribir
        heights = np.concatenate((heights1, heights2, heights3))
        self._write_heights(heights, file_path)

# Ejemplo de uso:
# gen = InputFileGenerator(line_length=500)
# gen.generate_random_walk('rw.txt', N=849000, sigma=2.0)
# gen.generate_noise('noise.txt', N=849000, low=0, high=8000)
# gen.generate_periodic('periodic.txt', N=849000, amplitude=1500, periods=10, offset=6000)
# gen.generate_mixed('mixed.txt', N=849000)
