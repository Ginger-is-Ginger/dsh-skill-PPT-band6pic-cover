# 🧣 丝带排版多图片样式 PPT封面生成 Skill

基于 Univer Office SDK 的指导 agent 自动生成 丝带排版多图片样式 PPT 封面的 Skill。

## 🎞️ 功能效果

⬇参考效果图与实现思路来自：[飘带PPT，用了不烧心！ -虎设PPT](https://www.bilibili.com/video/BV1WY446SEsv)

![Reference](./assets/ref.png "参考效果图")

⬇使用本 skill 与 [示例参考图](./assets/example_ref_img) 生成的封面图示例：

![Reference](./assets/example_output_shot.png "实际输出图")

本 Skill 需求6张用于填充排版的图片，交付包含1张丝带排版多图片样式 PPT 封面的 pptx 文件。原计划使用环境为 DeepSeek Harness，实际预计可运行于任何支持 Skill 与 Univer Office SDK 的 agent 环境。

## ⚡️ 快速开始

以 DeepSeek Harness WebUI 为例。

1. 安装插件：[dsh-univer-office](https://github.com/dream-num/dsh-univer-office)，使 DeepSeek Harness 接入 Univer Office SDK ，拥有较好的 Office 文件处理能力；

2. 将 silk-cover-page-replica 目录复制到 `~/.dsh/skills/` 或工作区目录下；

3. 准备 6 张用于填充丝带分格排版的素材图片，重命名为a.png 到 f.png（jpg亦可），放在工作区根目录；

4. 使用 DeepSeek-V41-Flash 模型，思考强度 Low ，使用以下提示词，让 agent 生成 PPT 封面：

```text
用 silk-cover-page-replica 技能，在这个工作区从零做一张「丝绸封面页」幻灯片。

现状：根目录只有 7 张参考图（a–g，PNG 或 JPG，尺寸各不相同），没有任何 .univer / .pptx，
文件需要你自己新建。

按这个顺序做，不要跳步：
1. 先加载 univer、univer-slide，再用 skill 工具加载 silk-cover-page-replica；严格照它的
   SKILL.md 走阶段 A（A1–A6）→ 阶段 B（B1–B6）。脚本里的 <skill-base> 用技能工具返回的
   base directory，工作区用当前目录。
2. 新建 silk-cover.univer，在它的 draft worktree 里建一个 Slide Unit；新建单元自带的第 1 页
   就用它，不要 append 新页。
3. 所有坐标/尺寸只能来自技能里的 JSON 规格，禁止手敲或"目测调整"；自由曲线的 EMU 路径窗口
   校准（pin_freeform.js）不能省，顺序必须是"先 compile 再 pin"。
4. 阶段 A 完成后立刻导出 silk-cover-lineart.pptx 并跑
   python <skill-base>/scripts/verify_slide.py silk-cover-lineart.pptx <skill-base>，
   必须打印 VERDICT: REPLICA MATCHES SPEC。这一步要在阶段 B 之前做（阶段 B 会替换页面）。
5. 阶段 B 直接覆盖同一页（合并会消费掉那 10 个形状）：build_design.py → design_page.js →
   导出 silk-cover-design.pptx → 跑
   python <skill-base>/scripts/verify_design.py silk-cover-design.pptx build/design.json，
   必须打印 VERDICT: DESIGN MATCHES SPEC。
6. 参考图分配：a→12-1、b→12-2、c→12-3、d→12-4、e→12-5、f→12-6，g 不使用；如果图片是 .jpg
   文件名，按同样方式处理即可。
7. 最后把两条验收命令的真实输出贴给我，再给一张第 1 页截图（scale 1.5）。

已知且不用处理的现象：截图里会出现虚线「Click to add a title / text」，那是画布占位符，不是
页面元素（elementCounts 里 text 必须为 0）；渐变描边在画布上按纯色渲染，渐隐效果只能看导出
XML —— 以 verify_design.py 的结果为准，不要为了"看起来有渐变"去改参数。

不要做：手改 build/design.json 或 build/design_page.js；自己另画一条曲线；跳过 pin 或跳过
任一验收命令。
```

5. silk-cover-design.pptx 即为最终交付物。

## ⚠️ 注意事项

- **填充图片对齐逻辑：**将图片大小保留比例调整至恰好能完全覆盖待填充网格的矩形包络，居中填充，效果是图片中心位于待填充网格的矩形包络中心，如果需要调整位置且保证不出现重复，需要在交付物中自行放大填充图片比例（PowerPoint 2021操作：形状格式 - 形状样式 - 形状选项 - 填充 - 图片或纹理填充 - 刻度X & 刻度Y）；

- **需要调整网格排版位置与大小：**选中所有网格，组合，然后调整位置与大小。


## ⛓‍💥 未完美复刻部分

由于参考教程视频过程并不完整，参考效果图中的部分效果本 skill 的交付物未完全复刻，具体包括：

1. **丝带第一张填充图片左侧透明度渐变效果**：参考教程视频未包含，可尝试向 agent 追加一轮 prompt 实现：

```text
为12-1元素填充图片添加渐变透明度效果，左起0%部分透明度100%，20%部分透明度0%
```

需要注意的是，实际上 Univer Office SDK 与较低版本 PowerPoint 无该功能，开发测试时 agent 的实现是通过编写 Python 脚本将 a.png 编辑为指定渐变透明样式的新 png 图片实现的。

2. **左侧标题文字、图章与背景图片**：参考教程视频未包含，均可通过简单的人工编辑自行添加。

## 📚️ 参考文献

参考效果图与实现思路来自：[飘带PPT，用了不烧心！ -虎设PPT](https://www.bilibili.com/video/BV1WY446SEsv)，一位优秀的 PPT 设计教程博主

测试 agent ：[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)

PowerPoint 编辑能力：[Univer Office SDK](https://github.com/dream-num/univer)

DeepSeek Harness 接入 Univer Office SDK 插件：[dsh-univer-office](https://github.com/dream-num/dsh-univer-office)

本 skill 使用 DeepSeek-V41-Flash 模型编写，过程中各轮的提示词记录：[提示词记录](./assets/skill_write_prompts.txt)

## 🫶 致谢

- 参考效果图与实现思路来自：[飘带PPT，用了不烧心！ -虎设PPT](https://www.bilibili.com/video/BV1WY446SEsv)，一位优秀的 PPT 设计教程博主；

- 本 skill 全程使用 DeepSeek-V41-Flash 模型编写，仅花费2.3（skill 编写）+0.2（新工作区测试）=2.5元。~~**大肥鱼牛逼！**~~

## 📄 开源协议

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 协议开源。
