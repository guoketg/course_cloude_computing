import argparse
from .common import ROOT, emit, write_json


def main():
    parser = argparse.ArgumentParser(description='BDP: cloud data and AI evidence lab kit')
    sub = parser.add_subparsers(dest='command', required=True)
    identity = sub.add_parser('identity')
    identity.add_argument('--student-id', required=True)
    identity.add_argument('--lab', default='01')
    identity.add_argument('--stage', default='start')
    seed = sub.add_parser('seed')
    seed.add_argument('--rows', type=int, default=20000)
    l1 = sub.add_parser('lab01')
    l1.add_argument('--endpoint')
    sub.add_parser('lab02')
    l3 = sub.add_parser('lab03')
    l3.add_argument('--workers', type=int, default=2)
    l3.add_argument('--partitions', type=int, default=8)
    sub.add_parser('lab04')
    l5 = sub.add_parser('lab05')
    l5.add_argument('--mode', choices=['lexical', 'semantic'], default='lexical')
    l6 = sub.add_parser('lab06')
    l6.add_argument('--split', choices=['dev', 'test'], default='dev')
    l6.add_argument('--generator', choices=['extractive', 'ollama'], default='extractive')
    l7 = sub.add_parser('lab07')
    l7.add_argument('--requests', type=int, default=20)
    sub.add_parser('lab08')
    args = parser.parse_args()
    if args.command == 'identity':
        if not args.student_id.strip() or len(args.student_id) > 64:
            parser.error('student-id must contain 1-64 characters')
        write_json(ROOT / 'student.json', {'student_id': args.student_id})
        emit(args.lab, args.stage, {'identity_note': '标识仅用于证据关联，不构成身份认证或防伪签名。'})
    elif args.command in ['seed', 'lab01', 'lab02', 'lab03', 'lab04']:
        from . import pipeline
        kwargs = vars(args).copy()
        name = kwargs.pop('command')
        getattr(pipeline, name)(**kwargs)
    elif args.command in ['lab05', 'lab06']:
        from . import intelligence
        kwargs = vars(args).copy()
        name = kwargs.pop('command')
        getattr(intelligence, name)(**kwargs)
    elif args.command == 'lab07':
        from .service import lab07
        lab07(requests=args.requests)
    elif args.command == 'lab08':
        from .governance import lab08
        lab08()


if __name__ == '__main__':
    main()
