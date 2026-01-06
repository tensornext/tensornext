import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.sdk.client import AIRuntimeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit inference job to AI Runtime")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Input prompt text",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )

    args = parser.parse_args()

    client = AIRuntimeClient(base_url=args.url, timeout=args.timeout)

    try:
        if not client.health_check():
            print("ERROR: Server health check failed", file=sys.stderr)
            sys.exit(1)

        response = client.infer(
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        print(f"Request ID: {response.request_id}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

