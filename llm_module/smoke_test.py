"""真实 API 连通性检查：会产生一次很小的模型调用。"""

from .client import LLMError, ask


def main() -> None:
    try:
        answer = ask("只回答四个字：连接成功", temperature=0, max_tokens=20)
    except LLMError as exc:
        raise SystemExit(f"连通性测试失败：{exc}") from exc
    print(answer)


if __name__ == "__main__":
    main()
