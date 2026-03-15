#!/bin/bash
mkdir -p data generated_policies data/chroma data/evidence
exec streamlit run streamlit_app/app.py \
  --server.port=${PORT:-8501} \
  --server.address=0.0.0.0 \
  --server.headless=true
