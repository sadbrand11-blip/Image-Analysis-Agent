"""Frozen general-natural RAG benchmark; historical C0/C1 is untouched."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('validate', 'prepare', 'dev', 'test', 'report'))
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--run-root', type=Path, default=Path(r'D:\CodexData\optical_agent\rag\general_v061\run_20261023'))
    parser.add_argument('--review-file', type=Path, help='Required for prepare; accepted provisional review bound to label SHA256')
    parser.add_argument('--model-path', type=Path, default=Path(r'D:\CodexData\optical_agent\rag\models\bge-small-zh-v1.5'))
    args = parser.parse_args(argv)
    # Help and command discovery do not import Torch or load any optional model.
    from optical_agent.general_rag_eval import load_inputs, prepare_run, run_split, write_report
    if args.stage == 'validate':
        dataset, corpora = load_inputs(args.repo)
        result = {'valid': True, 'questions': len(dataset['questions']),
                  'chunks': {key: len(value) for key, value in corpora.items()}, 'paid_api_requests': 0}
    elif args.stage == 'prepare':
        if args.review_file is None:
            parser.error('prepare requires --review-file; gold must be independently reviewed before retrieval')
        result = prepare_run(args.repo, args.run_root, review_file=args.review_file, model_path=args.model_path)
    elif args.stage in {'dev', 'test'}:
        result = run_split(args.repo, args.run_root, args.stage)
        result = {'split': result['split'], 'profiles': list(result['results']), 'paid_api_requests': 0}
    else:
        result = write_report(args.repo, args.run_root)['decision']
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
