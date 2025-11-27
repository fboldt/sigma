# SIGMA - Sistema Integrado de Geração de Mosaicos Aeroespaciais

Uma abordagem baseada em fusão de imagens e correspondência com imagens de satélite

## Descrição

Este repositório reúne o pipeline, os algoritmos e os experimentos para a geração de um ortomosaico contínuo e georreferenciado do estado do Espírito Santo, utilizando exclusivamente imagens de satélite.
O projeto explora técnicas modernas de image stitching (costura de imagens), com foco em reduzir a dependência de Ground Control Points (GCPs). O objetivo é produzir um mosaico adequado para aplicações ambientais, fundiárias, cartográficas e acadêmicas.


### Motivação

A consolidação de um ortomosaico estadual de alta qualidade é essencial para:
  - apoiar estudos territoriais e ambientais;
  - uniformizar análises cartográficas em nível estadual;
  - reduzir dependência de bases comerciais e de alto custo;
  - facilitar visualização e interpretação de áreas rurais e urbanas;
  - permitir comparações temporais para monitoramento ambiental.

No entanto, imagens orbitais podem variar entre si em resolução, iluminação, geometria e data de captura.
Este projeto busca superar esses desafios por meio de técnicas modernas de fusão, alinhamento e costura de imagens, garantindo que o mosaico final seja uniforme e geometricamente confiável.


### Objetivos

#### Objetivo Geral
Construir um ortomosaico do Espírito Santo reunindo cenas de satélite, registradas e fundidas com métodos robustos de visão computacional.

#### Objetivos Específicos
- Implementar os três algoritmos de fusão de imagens:

    - Weighted Average (WA)
    - Maxflow/Mincut
    - Laplacian Pyramid (LAP)

- Aplicar os algoritmos às imagens do satélite CBERS-4A após pré-processamento adequado.
- Gerar imagens compostas (mosaicos) a partir da fusão das cenas.
- Avaliar as imagens resultantes utilizando as seguintes métricas:
    - PSNR (Peak Signal-to-Noise Ratio)
    - SSIM (Structural Similarity Index)
    - MI (Mutual Information)
    - Coeficiente de Correlação (CC)
    - Tempo de execução dos algoritmos

- Comparar o desempenho dos métodos a partir da análise dos resultados quantitativos e qualitativos obtidos.


## Fluxo de trabalho

  #### 1. Coleta de imagens
  Download e organização das cenas orbitais selecionadas.
  
  #### 2. Análise das imagens
  Identificação de área de cobertura, nuvens, qualidade e resolução.
  
  #### 3. Ortorretificação
  Correções geométricas e radiométricas iniciais.
  
  #### 4. Posicionamento das imagens
  Registro geométrico e alinhamento entre cenas.

  #### 5. Mosaico e fusão
  Aplicação dos algoritmos de costura e geração do ortomosaico final.
Aplicação dos algoritmos de costura e geração do ortomosaico final.

