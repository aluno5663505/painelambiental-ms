# Painel Ambiental MS

Projeto acadêmico independente de consulta pública sobre consumo de etanol e estimativa de CO₂e direto evitado em serviço de transporte equivalente. Não é portal institucional oficial nem inventário certificado.

## Arquitetura

- HTML, CSS e JavaScript sem dependências externas;
- GitHub Pages para hospedagem e HTTPS;
- Name.com para domínio e DNS;
- GitHub Actions para testes e publicação diária;
- dados históricos somente agregados por período, entidade e unidade;
- nenhuma placa, hash, modelo individual, documento bruto ou banco SQLite no site.

O SQLite e os relatórios permanecem no ambiente local. `scripts/exportar_dados_publicos.py` lê o banco em modo somente leitura e exporta campos explicitamente permitidos.

## Dados demonstrativos

O calendário de 19/10/2026 a 18/12/2026 é sintético, agregado e identificado com `origem = SIMULADO`. Foi previamente calculado pelo motor da metodologia 1.0, com semente 5663505 e calibração histórica de 2026. O calendário é público neste repositório, mas não integra o pacote servido pelo Pages: o workflow inclui somente datas alcançadas em `data/indicadores.json`.

O agendamento ocorre às 10:23 UTC (06:23 de Campo Grande), sujeito a atrasos do GitHub. Workflows agendados em repositórios públicos podem ser desativados após inatividade; devem ser acompanhados durante a campanha. Não é integração em tempo real.

## Validação local

```sh
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/preparar_site.py
node --check assets/app.js
```

O diretório `dist/` contém apenas os arquivos permitidos para hospedagem.

## Publicação

Configurar Settings → Pages → Source como **GitHub Actions**. O workflow `pages.yml` publica por push, execução manual ou agendamento diário. Não usa secrets ou tokens pessoais; somente o `GITHUB_TOKEN` temporário com permissões mínimas.

## Metodologia

Consulte `metodologia.html` para fronteira, fórmula, constantes, hipóteses, limitações e referências IPCC/ANP/Inmetro. Os cenários de sensibilidade não são intervalos estatísticos de confiança. O resultado não representa emissões de ciclo de vida nem compensação de carbono.

## Licença

MIT para o código autoral. A licença não concede direitos sobre marcas, dados institucionais, relatórios de terceiros ou documentos acadêmicos. Não são utilizados logotipos institucionais.
