from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base = Path(r'c:\Users\JJE\Desktop\Projetos\Inflação')
csv_path = base / 'inflacao.csv'
out_dir = base / 'dashboard_inflacao'
out_dir.mkdir(exist_ok=True)

# Load data

df = pd.read_csv(csv_path, encoding='utf-8')
df['date'] = pd.to_datetime(df['referencia'] + '-01', format='%Y-%m-%d')
for col in ['ipca_variacao', 'ipca_acumulado_ano', 'ipca_acumulado_doze_meses', 'ipca15_variacao', 'ipca15_acumulado_ano', 'ipca15_acumulado_doze_meses', 'inpc_variacao', 'inpc_acumulado_ano', 'inpc_acumulado_doze_meses', 'ipa_variacao', 'ipa_acumulado_ano', 'ipc_fipe_variacao', 'ipc_fipe_acumulado_ano', 'incc_variacao', 'incc_acumulado_ano', 'incc_m_variacao', 'incc_m_acumulado_ano', 'selic_meta', 'selic_ano', 'juros_reais', 'salario_minimo']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

annual_levels = df.sort_values(['ano', 'mes']).groupby('ano').tail(1).copy()
annual_levels['ano'] = annual_levels['ano'].astype(int)

summary = {
    'periodo': f"{df['referencia'].iloc[0]} a {df['referencia'].iloc[-1]}",
    'pico_mensal': df.loc[df['ipca_variacao'].idxmax()],
    'pico_12m': df.loc[df['ipca_acumulado_doze_meses'].idxmax()],
    'ano_pior': annual_levels.loc[annual_levels['ipca_acumulado_ano'].idxmax()],
    'media_mensal': round(df['ipca_variacao'].mean(), 2),
    'inflacao_2020': annual_levels.loc[annual_levels['ano'] == 2020, 'ipca_acumulado_ano'].iloc[0],
    'inflacao_2021': annual_levels.loc[annual_levels['ano'] == 2021, 'ipca_acumulado_ano'].iloc[0],
    'inflacao_2022': annual_levels.loc[annual_levels['ano'] == 2022, 'ipca_acumulado_ano'].iloc[0],
    'inflacao_2023': annual_levels.loc[annual_levels['ano'] == 2023, 'ipca_acumulado_ano'].iloc[0],
}

# Chart 1: Monthly IPCA variation
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df['date'], df['ipca_variacao'], color='#1f77b4', linewidth=2)
ax.fill_between(df['date'], df['ipca_variacao'], 0, where=df['ipca_variacao'] >= 0, color='#1f77b4', alpha=0.18)
ax.axhline(0, color='#333333', linewidth=1)
ax.set_title('IPCA mensal: evolução da variação de preços', fontsize=16, weight='bold')
ax.set_xlabel('Data')
ax.set_ylabel('Variação mensal (%)')
ax.grid(True, linestyle='--', alpha=0.35)
ax.annotate(f"Pico histórico: {summary['pico_mensal']['ipca_variacao']:.2f}%\n({summary['pico_mensal']['referencia']})",
            xy=(summary['pico_mensal']['date'], summary['pico_mensal']['ipca_variacao']),
            xytext=(pd.Timestamp('1988-01-01'), 35),
            textcoords='data',
            color='crimson',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.8),
            arrowprops=dict(arrowstyle='->', color='crimson'))
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(out_dir / 'chart_ipca_variacao.png', dpi=200)
plt.close(fig)

# Chart 2: Recent 12-month accumulation
recent = df[df['date'] >= '2000-01-01'].copy()
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(recent['date'], recent['ipca_acumulado_doze_meses'], color='#1f77b4', linewidth=2.3, label='IPCA (12 meses)')
ax.plot(recent['date'], recent['inpc_acumulado_doze_meses'], color='#ff7f0e', linewidth=2.3, label='INPC (12 meses)')
ax.set_title('IPCA e INPC acumulados em 12 meses', fontsize=16, weight='bold')
ax.set_xlabel('Data')
ax.set_ylabel('Acumulado em 12 meses (%)')
ax.grid(True, linestyle='--', alpha=0.35)
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(out_dir / 'chart_ipca_inpc_12m.png', dpi=200)
plt.close(fig)

# Chart 3: Top annual inflation years
annual = annual_levels[['ano', 'ipca_acumulado_ano', 'inpc_acumulado_ano', 'ipa_acumulado_ano']].copy()
annual = annual.sort_values('ipca_acumulado_ano', ascending=False).head(10)
annual = annual.sort_values('ano')
fig, ax = plt.subplots(figsize=(12, 7))
bar_width = 0.25
years = annual['ano'].astype(int)
ax.bar(years - bar_width / 2, annual['ipca_acumulado_ano'], width=bar_width, label='IPCA', color='#1f77b4')
ax.bar(years + bar_width / 2, annual['inpc_acumulado_ano'], width=bar_width, label='INPC', color='#ff7f0e')
ax.set_title('Top 10 anos de maior inflação anual (IPCA e INPC)', fontsize=16, weight='bold')
ax.set_xlabel('Ano')
ax.set_ylabel('Inflação acumulada anual (%)')
ax.grid(True, axis='y', linestyle='--', alpha=0.35)
ax.legend()
fig.tight_layout()
fig.savefig(out_dir / 'chart_top_anos.png', dpi=200)
plt.close(fig)

# Chart 4: Recent Selic and real interest rate
recent2 = df[df['date'] >= '2010-01-01'].copy()
fig, ax = plt.subplots(figsize=(13, 6))
ax.plot(recent2['date'], recent2['selic_meta'], color='#2ca02c', linewidth=2.3, label='Meta da Selic (%)')
ax.plot(recent2['date'], recent2['juros_reais'], color='#d62728', linewidth=2.3, label='Juros reais (%)')
ax.set_title('Selic e juros reais na série recente', fontsize=16, weight='bold')
ax.set_xlabel('Data')
ax.set_ylabel('Taxa (%)')
ax.grid(True, linestyle='--', alpha=0.35)
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(out_dir / 'chart_selic_juros_reais.png', dpi=200)
plt.close(fig)

# Create HTML report
html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dashboard de Inflação no Brasil</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f5f7fb;
      color: #1d2430;
    }}
    .container {{ width: min(1200px, 94vw); margin: 0 auto; padding: 30px 0 80px; }}
    h1 {{ font-size: 2.1rem; margin-bottom: 10px; }}
    h2 {{ margin-top: 40px; font-size: 1.5rem; }}
    .subtitle {{ color: #4b5a6a; margin-bottom: 25px; }}
    .cards {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px; margin: 24px 0 28px;
    }}
    .card {{
      background: white; border-radius: 12px; padding: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      border-left: 5px solid #1f77b4;
    }}
    .card .label {{ display: block; font-size: 0.72rem; text-transform: uppercase; color: #607086; letter-spacing: 0.08em; }}
    .card .value {{ display: block; margin-top: 8px; font-size: 1.2rem; font-weight: bold; }}
    .chart {{
      background: white; border-radius: 14px; padding: 18px; margin-top: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }}
    .chart img {{ width: 100%; height: auto; display: block; border-radius: 10px; }}
    .analysis {{
      margin-top: 12px; font-size: 1.02rem; line-height: 1.7; color: #2b3a4c;
    }}
    .strong {{ font-weight: bold; }}
    footer {{ margin-top: 40px; color: #607086; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Dashboard de Inflação no Brasil</h1>
    <div class="subtitle">Dados do arquivo de referência: <span class="strong">{summary['periodo']}</span></div>

    <div class="cards">
      <div class="card">
        <span class="label">Pico mensal do IPCA</span>
        <span class="value">{summary['pico_mensal']['ipca_variacao']:.2f}%</span>
      </div>
      <div class="card">
        <span class="label">Data do pico mensal</span>
        <span class="value">{summary['pico_mensal']['referencia']}</span>
      </div>
      <div class="card">
        <span class="label">Pico em 12 meses</span>
        <span class="value">{summary['pico_12m']['ipca_acumulado_doze_meses']:.2f}%</span>
      </div>
      <div class="card">
        <span class="label">Ano mais inflacionado</span>
        <span class="value">{int(summary['ano_pior']['ano'])}</span>
      </div>
      <div class="card">
        <span class="label">Média mensal do IPCA</span>
        <span class="value">{summary['media_mensal']:.2f}%</span>
      </div>
    </div>

    <section class="chart">
      <h2>1) Volatilidade mensal do IPCA</h2>
      <img src="dashboard_inflacao/chart_ipca_variacao.png" alt="Variação mensal do IPCA" />
      <div class="analysis">
        A série mensal do IPCA mostra claramente a diferença entre os ciclos hiperinflacionários dos anos 1980 e início dos 1990 e os períodos de inflação moderada que predominam após 1994. O ponto mais extremo da curva foi em <span class="strong">{summary['pico_mensal']['referencia']}</span>, quando a variação mensal chegou a <span class="strong">{summary['pico_mensal']['ipca_variacao']:.2f}%</span>. Esse salto evidência como a política de estabilização e o regime de metas inflacionárias transformaram o comportamento da inflação no país.
      </div>
    </section>

    <section class="chart">
      <h2>2) IPCA e INPC acumulados em 12 meses</h2>
      <img src="dashboard_inflacao/chart_ipca_inpc_12m.png" alt="IPCA e INPC em 12 meses" />
      <div class="analysis">
        A comparação entre IPCA e INPC em 12 meses revela como a inflação de consumo se comportou ao longo do tempo, especialmente nos ciclos de alta e de queda. O pico mais elevado do acumulado em 12 meses foi em <span class="strong">{summary['pico_12m']['referencia']}</span>, com <span class="strong">{summary['pico_12m']['ipca_acumulado_doze_meses']:.2f}%</span>. O gráfico também mostra que o período recente, especialmente 2021-2022, teve escalada de preços acima do habitual, mas muito menos extrema do que as fases hiperinflacionárias históricas.
      </div>
    </section>

    <section class="chart">
      <h2>3) Top 10 anos de maior inflação anual</h2>
      <img src="dashboard_inflacao/chart_top_anos.png" alt="Top anos de inflação anual" />
      <div class="analysis">
        Nos anos mais severos, o IPCA anual foi muito acima da média histórica. O maior nível anual observado foi <span class="strong">{summary['ano_pior']['ipca_acumulado_ano']:.2f}%</span> em <span class="strong">{int(summary['ano_pior']['ano'])}</span>. Esse padrão reforça a ideia de que a inflação no Brasil foi marcada por ciclos de aceleração e desalinhamento entre preços, renda e política monetária. O conjunto de 2020 a 2023, por outro lado, mostra um choque de preços mais contido em comparação com os picos da década de 1980 e 1990.
      </div>
    </section>

    <section class="chart">
      <h2>4) Selic e juros reais na série recente</h2>
      <img src="dashboard_inflacao/chart_selic_juros_reais.png" alt="Selic e juros reais" />
      <div class="analysis">
        A comparação entre a meta da Selic e os juros reais ajuda a entender a relação entre política monetária e custo do crédito. Quando a taxa nominal está acima da inflação, os juros reais ficam positivos, o que pode desacelerar a demanda e reduzir pressões inflacionárias. Em contraste, quando a taxa real cai para níveis baixos ou negativos, a dinâmica tende a estimular gasto e pode pressionar o nível de preços. A série recente revela justamente esse equilíbrio entre tentativa de controle inflacionário e condições de financiamento.
      </div>
    </section>

    <section class="chart">
      <h2>Conclusão</h2>
      <div class="analysis">
        O conjunto de gráficos indica que a inflação brasileira passou por extremos muito mais severos na segunda metade do século XX do que nos últimos anos. A trajetória do IPCA mensal confirma que o problema histórico não foi pontual, mas estrutural e cíclico. Mesmo assim, os dados mais recentes mostram que a inflação pode voltar a acelerar rapidamente quando há choques de oferta, liquidez ou pressões de custos, por isso a análise temporal continua fundamental para orientar políticas públicas e decisões de mercado.
        <br><br>
        Em termos agregados, os valores observados em 2020, 2021, 2022 e 2023 foram: <span class="strong">{summary['inflacao_2020']:.2f}%</span>, <span class="strong">{summary['inflacao_2021']:.2f}%</span>, <span class="strong">{summary['inflacao_2022']:.2f}%</span> e <span class="strong">{summary['inflacao_2023']:.2f}%</span> de variação anual acumulada do IPCA, mostrando que a última fase foi mais moderada, mas ainda relevante.
      </div>
    </section>

    <footer>Dashboard gerado a partir do arquivo de dados de inflação do Brasil.</footer>
  </div>
</body>
</html>
'''
(base / 'inflacao_dashboard.html').write_text(html, encoding='utf-8')

print('Dashboard gerado com sucesso:')
print(base / 'inflacao_dashboard.html')
print('Dados resumidos:')
print(f"Período: {summary['periodo']}")
print(f"Pico IPCA mensal: {summary['pico_mensal']['referencia']} = {summary['pico_mensal']['ipca_variacao']:.2f}%")
print(f"Pico IPCA 12m: {summary['pico_12m']['referencia']} = {summary['pico_12m']['ipca_acumulado_doze_meses']:.2f}%")
print(f"Ano com maior IPCA anual: {int(summary['ano_pior']['ano'])} = {summary['ano_pior']['ipca_acumulado_ano']:.2f}%")
