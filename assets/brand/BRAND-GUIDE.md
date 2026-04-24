# NL Imóveis — Brand Guide (pra aplicar no app Streamlit)

Baseado no **Manual de Marca NL Imóveis** (oficial, 28/01/2025).
Cliente: NL Imóveis · CRECI 1440 J · Natal/RN · Atuando desde 1997.

---

## 🎨 Paleta de Cores OFICIAL

### Principais (obrigatório usar)
| Nome | HEX | RGB | Uso recomendado |
|---|---|---|---|
| **Azul Noturno** | `#033677` | 3, 54, 119 | Primária institucional · Header, sidebar, títulos, links |
| **Ouro Vivo** | `#FFB700` | 255, 183, 0 | Primária destaque · Botões primários, badges de destaque, CTAs |

### Secundária
| Nome | HEX | RGB | Uso |
|---|---|---|---|
| **Céu Claro** | `#F3F6FA` | 243, 246, 250 | Fundos claros, bordas sutis, separadores |

### Complementares (usar com moderação)
| Nome | HEX | RGB | Uso |
|---|---|---|---|
| **Sol Dourado** | `#FFDE76` | 255, 222, 118 | Highlights suaves, hover states |
| **Azul Horizonte** | `#2678BC` | 38, 120, 188 | Badges info, estados secundários |
| **Azul Profundo** | `#001833` | 0, 24, 51 | Texto sobre fundo claro, contraste máximo |
| **Terra Fértil** | `#9B5400` | 155, 84, 0 | Detalhes gráficos, separadores pontuais |

### Estados semânticos (manter do Streamlit ou mapear pra paleta)
| Estado | HEX sugerido | Observação |
|---|---|---|
| Sucesso | `#16A34A` | Verde padrão (ok manter) |
| Erro | `#DC2626` | Vermelho padrão (ok manter) |
| Aviso | `#FFB700` | **Usar Ouro Vivo da marca** |
| Info | `#2678BC` | **Usar Azul Horizonte da marca** |

---

## 🔤 Tipografia

### Fonte primária: **Georama**
- Uso: títulos, cabeçalhos, KPIs em destaque
- Arquivo: `assets/brand/fonts/Georama-Regular.ttf` + variações WOFF2
- Peso regular pra títulos, Medium/Bold pra ênfase

### Fonte de apoio: **Multa Pecunia**
- Uso: detalhes, legendas, citações, pequenos textos (rodapé, hints)
- Arquivo: `assets/brand/fonts/MultaPecunia.ttf` / `.woff2`
- Usar com moderação — é decorativa

### Fallback
```css
font-family: "Georama", -apple-system, "Segoe UI", sans-serif;
```

---

## 🏷️ Logo

### Arquivos disponíveis em `assets/brand/logo/`
- `nl-logo-principal.png` — logo padrão (prioridade)
- `nl-logo-azul.png` — versão azul, mais presença
- Pra versão branca (fundo escuro): usar CSS `filter: brightness(0) invert(1)` ou converter depois

### Onde usar no app
- **Header principal:** logo à esquerda, alinhado com o título
- **Tela de login:** logo centralizado, tamanho maior (destaque)
- **Sidebar:** logo pequeno (~40px) acima do nome do usuário
- **Favicon** (aba do navegador): usar logo quadrada se disponível

---

## 💬 Slogans e textos oficiais

### Slogan principal
**"Imóveis em Natal"**
**"compre. venda. alugue."**

### Propósito da marca
> Oferecer serviços imobiliários diferenciados, com foco na **segurança, confiança e satisfação** dos clientes.

### Cobertura geográfica
Natal/RN · Parnamirim · São Miguel do Gostoso · litorais do RN

### 6 Valores da NL
1. Ética
2. Confiança
3. Excelência
4. Agilidade
5. Responsabilidade
6. Conexão

### Rodapé sugerido
```
NL Imóveis · CRECI 1440 J · Natal/RN
Atuando desde 1997 · nladmmarketing@gmail.com
```

---

## 🚫 Don'ts (Manual da Marca, p.7)

Não fazer com o logo:
- ❌ Desrespeitar as margens de segurança
- ❌ Distorcer desproporcionalmente
- ❌ Rotacionar
- ❌ Usar cores fora da paleta
- ❌ Aplicar contornos
- ❌ Alterar elementos internos do logo

---

## 🎯 Tom de voz

### Características
- **Profissional mas próximo** — imobiliária tradicional (desde 1997) com tom moderno
- **Claro e direto** — cliente precisa entender rápido
- **Confiante sem ser arrogante** — reforçar expertise sem vender arrogância
- **Acolhedor** — o cliente está tomando decisão importante (comprar/alugar casa)

### Exemplos de textos para o app
- ✅ "Bem-vindo, {nome}. Seu painel de performance está pronto."
- ✅ "Confira as vendas do trimestre"
- ❌ "Oi gente! Seu dashboard super legal 🚀"
- ❌ "Métricas corporativas consolidadas para análise multidimensional"

---

## 🎨 Como aplicar no Streamlit

### 1. Carregar fontes custom
```python
# em app.py, dentro de um st.markdown com unsafe_allow_html=True
<style>
@font-face {
    font-family: 'Georama';
    src: url('./assets/brand/fonts/Georama-Medium.woff2') format('woff2');
    font-weight: 500;
}
@font-face {
    font-family: 'Georama';
    src: url('./assets/brand/fonts/Georama-Regular.ttf') format('truetype');
    font-weight: 400;
}
@font-face {
    font-family: 'MultaPecunia';
    src: url('./assets/brand/fonts/MultaPecunia.woff2') format('woff2');
}

html, body, [class*="st-"] {
    font-family: 'Georama', -apple-system, sans-serif;
}
</style>
```

### 2. Variáveis CSS da paleta
```css
:root {
    --nl-azul-noturno: #033677;
    --nl-ouro-vivo: #FFB700;
    --nl-ceu-claro: #F3F6FA;
    --nl-sol-dourado: #FFDE76;
    --nl-azul-horizonte: #2678BC;
    --nl-azul-profundo: #001833;
    --nl-terra-fertil: #9B5400;
}
```

### 3. Logo no header
```python
import streamlit as st
from pathlib import Path

logo_path = Path(__file__).parent / "assets" / "brand" / "logo" / "nl-logo-principal.png"
st.image(str(logo_path), width=200)
```

### 4. `.streamlit/config.toml` (tema do Streamlit)
```toml
[theme]
base = "light"
primaryColor = "#033677"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F6FA"
textColor = "#001833"
font = "sans serif"
```

---

## ✅ Checklist de aplicação (pra conferir depois)

- [ ] Tema Streamlit configurado em `.streamlit/config.toml` com Azul Noturno
- [ ] Fontes Georama/Multa Pecunia carregadas via `@font-face`
- [ ] Logo aparece no header e no login
- [ ] KPIs usam Azul Noturno pros títulos, Ouro Vivo pros destaques
- [ ] Botão primário usa Ouro Vivo (não o verde padrão do Streamlit)
- [ ] Sidebar em Azul Noturno com texto branco/claro
- [ ] Rodapé menciona CRECI 1440 J, Natal/RN, ano de fundação
- [ ] Textos revisados pro tom de voz NL (profissional + próximo)
- [ ] Slogan "Imóveis em Natal · compre. venda. alugue" visível em algum lugar
- [ ] Favicon atualizado (se possível)
