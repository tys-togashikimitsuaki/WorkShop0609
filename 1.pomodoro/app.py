"""
Flask アプリケーション エントリーポイント

ルートは薄く保ち、ビジネスロジックはドメイン層（pomodoro/）に委譲する。
create_app() ファクトリにより、テスト時に PomodoroTimer / StatsService を
任意の実装に差し替えられる（依存性注入）。
"""

import os
from flask import Flask, jsonify, render_template, request

from pomodoro.timer import PomodoroTimer
from pomodoro.stats import JsonStatsRepository, StatsService


def create_app(timer: PomodoroTimer | None = None, stats_service: StatsService | None = None) -> Flask:
    """アプリケーションファクトリ。

    Args:
        timer: 使用する PomodoroTimer インスタンス（省略時は新規作成）。
        stats_service: 使用する StatsService インスタンス（省略時は JsonStatsRepository で作成）。

    Returns:
        設定済みの Flask アプリケーション。
    """
    _app = Flask(__name__)

    if timer is None:
        timer = PomodoroTimer()
    if stats_service is None:
        stats_service = StatsService(
            JsonStatsRepository(filepath=os.path.join(os.path.dirname(__file__), "stats.json"))
        )

    # ---------------------------------------------------------------------------
    # ページ
    # ---------------------------------------------------------------------------

    @_app.get("/")
    def index():
        return render_template("index.html")

    # ---------------------------------------------------------------------------
    # タイマー API
    # ---------------------------------------------------------------------------

    @_app.get("/api/state")
    def api_state():
        return jsonify(timer.to_dict())

    @_app.post("/api/start")
    def api_start():
        timer.start()
        return jsonify(timer.to_dict())

    @_app.post("/api/pause")
    def api_pause():
        timer.pause()
        return jsonify(timer.to_dict())

    @_app.post("/api/reset")
    def api_reset():
        timer.reset()
        return jsonify(timer.to_dict())

    @_app.post("/api/complete")
    def api_complete():
        """クライアントからセッション完了を通知する。統計を記録し次のモードに切り替える。"""
        data = request.get_json(silent=True) or {}
        duration = int(data.get("duration_seconds", 0))
        mode = timer.mode.value
        if mode == "work" and duration > 0:
            stats_service.record_work_session(duration)
        timer.complete_session()
        return jsonify(timer.to_dict())

    # ---------------------------------------------------------------------------
    # 統計 API
    # ---------------------------------------------------------------------------

    @_app.get("/api/stats")
    def api_stats():
        return jsonify(stats_service.get_today_stats())

    return _app


# 本番用インスタンス
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

