#!/bin/bash
cd "$(dirname "$0")"
echo "Organizando juegos en carpetas independientes..."
python3 build-index.py
echo ""
read -p "Presiona Enter para cerrar..."
