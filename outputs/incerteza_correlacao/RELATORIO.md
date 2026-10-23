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

## 2. Conferência

| Checagem | Resultado | Detalhe |
|---|---|---|
| independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %) | ok | maior desvio 0,12 % |
| tudo, ρ = 1: p5 e p95 = N4 com tudo no quantil 5 % e 95 % (±1 %) | ok | 2.705,1–11.764,6 mi; maior desvio 0,49 % |
| quantil 0 e 1 de tudo = faixa mín–máx do snapshot (±0,1 %) | ok | 1.882,6–15.576,9 mi contra 1.882,6–15.576,9 |

## Como ler

- ρ = 0 é a leitura de `build_incerteza_cp2b.py`. Com ρ = 1 num grupo, o grupo inteiro fica no mesmo quantil das suas faixas em cada sorteio; tudo com ρ = 1 vai de ponta a ponta da faixa mín–máx do CP2b.
- `elemento` é a correlação mais defensável para o BMP (o mesmo método de laboratório) e para FC, FS e FL (a mesma leitura da definição); `substrato` é a correlação de quem tira todos os fatores de um substrato da mesma fonte; `cana` mede só o peso de a cana andar junta.
- O Spearman p5 e o top 50 dizem se o ranking municipal aguenta a correlação: quando tudo sobe ou desce junto, o ranking tende a ficar mais estável que o total, porque os municípios andam juntos.
- O intervalo de cada estrutura é o que se tem se aquela correlação for verdadeira; não há aqui uma estimativa de qual ρ é o real.

