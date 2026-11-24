#!/usr/bin/env bash
# Downloads Netflix's public viewing data into data/
set -e
mkdir -p data && cd data
curl -sSL -o g.tsv "https://www.netflix.com/tudum/top10/data/all-weeks-global.tsv"
curl -sSL -o wwh_2024H2.xlsx "https://assets.ctfassets.net/4cd45et68cgf/6XSmoEjBjVMPRtYybT9d1E/8c0b0b2645b8712d5597b0bdbe0d64e2/What_We_Watched_A_Netflix_Engagement_Report_2024Jul-Dec.xlsx"
curl -sSL -o wwh_2025H1.xlsx "https://assets.ctfassets.net/4cd45et68cgf/mplcXj5ulHDfbCPCr0f0I/5dbb6ec09f03df89706476e380e9b8bd/What_We_Watched_A_Netflix_Engagement_Report_2025Jan-Jun.xlsx"
curl -sSL -o wwh_2025H2.xlsx "https://assets.ctfassets.net/4cd45et68cgf/2vdDPGLKA0XX2cjF2APJFn/7f1c367b39ed73a6a588751d3c5d0252/What_We_Watched_A_Netflix_Engagement_Report_2025Jul-Dec__6_.xlsx"
curl -sSL -o wwh_2026H1.xlsx "https://assets.ctfassets.net/4cd45et68cgf/40WGcHJa9vRua31kU6Gbz5/43b15c7fbd6924392fc80e885839e39f/Netflix-s_What_We_Watched_Report_2026Jan-Jun__1_.xlsx"
echo "done"
