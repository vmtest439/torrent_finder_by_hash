import time
import argparse
import json
from datetime import datetime
from typing import Dict, Set, List, Tuple, Any

import libtorrent as lt


def hex_to_sha1_hash(hex_hash: str) -> lt.sha1_hash:
    """Convert a hexadecimal string to a SHA-1 hash object"""
    hash_bytes = bytes.fromhex(hex_hash)
    return lt.sha1_hash(hash_bytes)


def scan_dht_for_info_hashes(torrent_hashes: List[str]) -> Dict[str, Any]:
    """Scan the DHT for info hashes and their peers"""
    settings = {
        'alert_mask': lt.alert.category_t.all_categories,
        'enable_upnp': False,
        'enable_natpmp': False,
        'listen_interfaces': '0.0.0.0:6881',
    }

    ses = lt.session(settings)
    ses.add_dht_router("router.bittorrent.com", 6881)
    ses.add_dht_router("dht.transmissionbt.com", 6881)
    ses.add_dht_router("router.utorrent.com", 6881)

    print("Waiting for DHT to load...")
    time.sleep(10)

    results: Dict[str, Any] = {"date_crawling": datetime.now().isoformat()}

    print("Starting DHT scan...")
    try:
        for torrent_hash in torrent_hashes:
            target_hash = hex_to_sha1_hash(torrent_hash)
            ses.dht_get_peers(target_hash)

            print(f"Scanning for hash: {torrent_hash}...")

            peers: Set[Tuple[str, int]] = set()
            start_time = time.time()
            while time.time() - start_time < 30:  # Scan for 30 seconds per hash
                alerts = ses.pop_alerts()
                for alert in alerts:
                    if not isinstance(alert, lt.dht_get_peers_reply_alert):
                        continue
                    for peer in alert.peers():
                        if peer in peers:
                            continue
                        peers.add(peer)
                        print(f"Found peer {peer} for info_hash: {torrent_hash}")
                time.sleep(1)

            results[torrent_hash] = [f"{peer[0]}:{peer[1]}" for peer in peers]
            print(f"Finished scanning for hash: {torrent_hash}. Found {len(peers)} peers.")

    except KeyboardInterrupt:
        print("Scan stopped.")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan the DHT for torrent info hashes and peers.")
    parser.add_argument("--hash", type=str, help="Specify a single torrent hash to search for.")
    parser.add_argument("--hash-file", type=str, help="Specify a file containing a list of torrent hashes.")
    parser.add_argument("--output", type=str, default="output.json", help="Specify the output JSON file.")
    args = parser.parse_args()

    if args.hash:
        torrent_hashes = [args.hash]
    elif args.hash_file:
        with open(args.hash_file, "r") as f:
            torrent_hashes = [line.strip() for line in f.readlines()]
    else:
        print("Error: No hash or hash file provided! Use --hash <hash_str> or --hash-file <filepath>")
        return

    if not args.output:
        print("Error: No output file provided! Use --output <file>.json")
        return

    results = scan_dht_for_info_hashes(torrent_hashes)

    with open(args.output, "w") as res_file:
        json.dump(results, res_file, indent=4)

    print(f"Results saved to {args.output}.")


if __name__ == "__main__":
    main()
