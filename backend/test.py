from crawler import crawler

def main():
    url_file = 'url.txt'  # Ensure this points to your urls.txt file
    cr = crawler(None, url_file)
    cr.crawl()
    print("Inverted Index:", cr.get_inverted_index())
    print("Resolved Inverted Index:", cr.get_resolved_inverted_index())

if __name__ == "__main__":
    main()