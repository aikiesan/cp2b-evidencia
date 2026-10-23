# Incerteza do N4 do CP2b v5.1 com parâmetros correlacionados

> 20000 sorteios por configuração; volumes em milhões de Nm³ de CH₄ por ano. O mesmo modelo de `build_incerteza_cp2b.py` (que reproduz o mín, o med e o máx do snapshot), com grupos de parâmetros sorteados juntos por uma cópula gaussiana de correlação ρ. Cada parâmetro mantém a sua triangular (mín, med, máx) do CP2b; muda só o quanto eles andam juntos. Nada aqui muda a plataforma.

N4 med do CP2b: 5.971,7. Faixa mín–máx do snapshot: 1.882,6–15.576,9.

## 1. Intervalo de 90 % do N4 do estado

| Estrutura | O que anda junto | ρ | p5 | p50 | p95 | p5–p95 contra o med | Spearman p5 | Top 50 com ≥ 90 % |
|---|---|---:|---:|---:|---:|---|---:|---:|
| independente | cada parâmetro sozinho | 0,0 | 5.129,8 | 5.932,7 | 6.886,7 | -14,1 % a +15,3 % | 0,989 | 44 de 50 |
| substrato | todos os parâmetros de um substrato juntos | 0,5 | 4.760,7 | 6.104,2 | 7.899,6 | -20,3 % a +32,3 % | 0,977 | 37 de 50 |
| substrato | todos os parâmetros de um substrato juntos | 1,0 | 4.559,6 | 6.298,1 | 8.755,6 | -23,6 % a +46,6 % | 0,965 | 35 de 50 |
| elemento | o mesmo elemento em todos os substratos (todos os BMP, todos os FC, …) | 0,5 | 4.691,2 | 5.926,1 | 7.369,0 | -21,4 % a +23,4 % | 0,991 | 45 de 50 |
| elemento | o mesmo elemento em todos os substratos (todos os BMP, todos os FC, …) | 1,0 | 4.411,3 | 5.905,1 | 7.738,0 | -26,1 % a +29,6 % | 0,991 | 46 de 50 |
| cana | palha, bagaço, torta e vinhaça juntos; o resto independente | 1,0 | 3.448,8 | 5.905,5 | 10.176,6 | -42,2 % a +70,4 % | 0,979 | 44 de 50 |
| tudo | todos juntos | 0,5 | 3.411,5 | 5.960,4 | 9.752,1 | -42,9 % a +63,3 % | 0,984 | 44 de 50 |
| tudo | todos juntos | 1,0 | 2.691,7 | 5.953,4 | 11.815,2 | -54,9 % a +97,9 % | 0,976 | 44 de 50 |
| fonte | o mesmo elemento com uma referência em comum (o BMP de bagaço, palha e torta, …); valores da equipe sozinhos | 0,5 | 5.001,9 | 5.939,6 | 7.029,9 | -16,2 % a +17,7 % | 0,988 | 44 de 50 |
| fonte | o mesmo elemento com uma referência em comum (o BMP de bagaço, palha e torta, …); valores da equipe sozinhos | 1,0 | 4.892,2 | 5.926,2 | 7.173,4 | -18,1 % a +20,1 % | 0,988 | 44 de 50 |
| fonte_ampla | qualquer parâmetro com uma referência em comum, mesmo de elementos diferentes | 1,0 | 4.536,6 | 5.926,9 | 7.760,6 | -24,0 % a +30,0 % | 0,985 | 45 de 50 |
| fonte_equipe | fonte, e os valores da própria equipe (cp2b) de um mesmo elemento juntos | 1,0 | 4.738,3 | 5.936,1 | 7.356,1 | -20,7 % a +23,2 % | 0,988 | 45 de 50 |

## 2. Conferência

| Checagem | Resultado | Detalhe |
|---|---|---|
| independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %) | ok | maior desvio 0,12 % |
| tudo, ρ = 1: p5 e p95 = N4 com tudo no quantil 5 % e 95 % (±1 %) | ok | 2.705,1–11.764,6 mi; maior desvio 0,49 % |
| quantil 0 e 1 de tudo = faixa mín–máx do snapshot (±0,1 %) | ok | 1.882,6–15.576,9 mi contra 1.882,6–15.576,9 |

## 3. Os grupos por fonte

Grupos da estrutura `fonte` com mais de um parâmetro (o mesmo elemento citando uma referência em comum). Os grupos de `fonte_ampla` e `fonte_equipe` estão em `fontes.csv`.

| Parâmetros | Referências em comum |
|---|---|
| BAGACO BMP, PALHA BMP, TORTA_FILTRO BMP | talha2016_bagaco; velasquez2020_sugarcane |
| PALHA_MILHO BMP, PALHA_SOJA BMP | herrmann2012_corn |
| AVES_CORTE FL, AVES_POSTURA FL, BAGACO FL, BAGACO_CITROS FL, BOV_CONFINADO FL, BOV_LEITE FL, CASCA_CAFE FL, LODO_ETE FL, PALHA FL, PALHA_MILHO FL, PALHA_SOJA FL, PODA_URBANA FL, RSU_ORGANICO FL, SUINOS FL, TORTA_FILTRO FL, VINHACA FL | FL espacial do CP2b (fl_v5) |
| BAGACO ST, TORTA_FILTRO ST | talha2016_bagaco |
| BAGACO SV, TORTA_FILTRO SV | talha2016_bagaco |

- Valores da própria equipe, sem referência externa (59): AVES_CORTE FCo, AVES_CORTE FS, AVES_CORTE g, AVES_POSTURA FCo, AVES_POSTURA FS, AVES_POSTURA ST, BAGACO FS, BAGACO g, BAGACO_CITROS FC, BAGACO_CITROS FCo, BAGACO_CITROS FS, BAGACO_CITROS g, BOV_CONFINADO FCo, BOV_CONFINADO FS, BOV_LEITE FC, BOV_LEITE FCo, BOV_LEITE FS, BOV_PASTO_MISTO FC, BOV_PASTO_MISTO FCo, BOV_PASTO_MISTO FS, BOV_PASTO_MISTO g, CASCA_CAFE FC, CASCA_CAFE FCo, CASCA_CAFE FS, CASCA_CAFE g, LODO_ETE FCo, LODO_ETE FS, LODO_ETE ST, LODO_ETE g, PALHA FCo, PALHA FS, PALHA ST, PALHA g, PALHA_MILHO FC, PALHA_MILHO FCo, PALHA_MILHO FS, PALHA_MILHO g, PALHA_SOJA FC, PALHA_SOJA FCo, PALHA_SOJA FS, PALHA_SOJA g, PODA_URBANA FC, PODA_URBANA FCo, PODA_URBANA FS, PODA_URBANA g, RSU_ORGANICO FC, RSU_ORGANICO FCo, RSU_ORGANICO FS, SUINOS FC, SUINOS FCo, SUINOS FS, SUINOS g, TORTA_FILTRO FC, TORTA_FILTRO FCo, TORTA_FILTRO FS, VINHACA FC, VINHACA FCo, VINHACA FS, VINHACA direto.
- Fonte feedstocks.yaml, mas o yaml não tem refs para o código e o elemento: AVES_CORTE BMP, ST, SV; AVES_POSTURA BMP, SV; BOV_LEITE BMP, ST, SV; BOV_PASTO_MISTO BMP, FL, ST, SV; LODO_ETE BMP, SV; RSU_ORGANICO BMP, ST, SV, g; SUINOS BMP, SV.


## Como ler

- ρ = 0 é a leitura de `build_incerteza_cp2b.py`. Com ρ = 1 num grupo, o grupo inteiro fica no mesmo quantil das suas faixas em cada sorteio; tudo com ρ = 1 vai de ponta a ponta da faixa mín–máx do CP2b.
- `elemento` é a correlação mais defensável para o BMP (o mesmo método de laboratório) e para FC, FS e FL (a mesma leitura da definição); `substrato` é a correlação de quem tira todos os fatores de um substrato da mesma fonte; `cana` mede só o peso de a cana andar junta.
- O Spearman p5 e o top 50 dizem se o ranking municipal aguenta a correlação: quando tudo sobe ou desce junto, o ranking tende a ficar mais estável que o total, porque os municípios andam juntos.
- `fonte` é a correlação que as fontes citadas sustentam: o mesmo elemento anda junto quando cita a mesma referência. Onde `fonte` é feedstocks.yaml, as referências são as refs do yaml para aquele elemento, usadas só quando a faixa do yaml é a do arquivo. Um valor da equipe (`cp2b`) não cita fonte, e `fonte` o deixa sozinho; `fonte_equipe` põe os valores da equipe de um mesmo elemento juntos. `fonte_ampla` junta também elementos diferentes da mesma referência (o ST e o BMP do mesmo artigo), o que supõe que eles erram para o mesmo lado.
- O intervalo de cada estrutura é o que se tem se aquela correlação for verdadeira; não há aqui uma estimativa de qual ρ é o real.

