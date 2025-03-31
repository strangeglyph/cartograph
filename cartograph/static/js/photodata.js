class Photo {
  constructor(path, desc) {
    this.path = path;
    this.desc = desc;
  }
}

const PHOTO_DATA = [
  {
    position: [32.62, -116.5],
    photos: [
      new Photo("pct-terminus-south.png", "Der südliche PCT Terminus"),
      new Photo("family.jpg", "Meine Trail-Familie"),
    ]
  },
  {
    position: [32.68, -116.53],
    photos: [
      new Photo("mt-whitney.jpg", "Am Gipfel von Mt. Whitney"),
      new Photo("northern-terminus.jpg", "Geschafft"),
    ]
  },
]
