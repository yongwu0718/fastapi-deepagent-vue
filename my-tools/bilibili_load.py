from langchain_community.document_loaders import BiliBiliLoader

loader = BiliBiliLoader(
    video_urls=[
        "https://www.bilibili.com/video/BV17c12BMEMc?spm_id_from=333.788.videopod.sections&vd_source=7d37199ed13d30e125c7bcd29f78a8c9",],
    sessdata="767698b7%2C1799510939%2C1df64%2A72CjAscsGChpA4IpNLlYt505m88l-nYl8qGTGagRYO4ez2OxfUsVYnyD1E7fkfu_O7mBQSVlFIX1RnSXpIbTJXM2F3UWFQal9kTXJkNERSTlBaR2hHcHFGU2hxLUoxdGRXTW5KQTNwYjUxdkMxdHlSUXk0RENMcThoSV9QeFNhNlRwSFVEVFk1Ykx3IIEC",
    bili_jct="d0c02a53d47485789543f6f618f42850",
    buvid3="A5FB5A3E-41D3-BE24-8844-E29E5FDD862028978infoc",
)

print("⏳ 正在获取视频字幕...")
docs = loader.load()

# 2. 定义输出的 Markdown 文件名
output_filename = "bilibili_transcripts.md"

# 3. 将纯内容写入 Markdown 文件
with open(output_filename, "w", encoding="utf-8") as f:
    for i, doc in enumerate(docs):
        # 仅提取标题用于排版分隔，提取正文内容
        title = doc.metadata.get('title', f'未命名视频 {i+1}')
        content = doc.page_content
        
        # 写入视频标题
        f.write(f"# {title}\n\n")
        
        # 写入字幕正文
        if content and content.strip():
            f.write(f"{content}\n\n")
        else:
            f.write("*（该视频无字幕内容）*\n\n")
            
        # 添加分割线
        f.write("---\n\n")

print(f"✅ 完成！纯文本内容已写入至: {output_filename}")