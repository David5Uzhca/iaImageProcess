import { Component, ViewChild, ElementRef } from '@angular/core';
import { ImageService } from '../../services/image.service';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-upload',
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss'],
  imports: [CommonModule],
})
export class UploadComponent {
  selectedFile: File | null = null;
  predictionResult: any = null;
  images: any[] = [];
  isCameraOpen: boolean = false;
  captureMessage: string | null = null;

  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvasElement') canvasElement!: ElementRef<HTMLCanvasElement>;

  constructor(private imageService: ImageService) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    }
  }

  onUpload(): void {
    if (this.selectedFile) {
      const allowedTypes = ['image/jpeg', 'image/png'];
      if (!allowedTypes.includes(this.selectedFile.type)) {
        console.error('Error: Formato de archivo no permitido.');
        return;
      }

      const maxSize = 5 * 1024 * 1024; // 5 MB
      if (this.selectedFile.size > maxSize) {
        console.error('Error: El archivo es demasiado grande.');
        return;
      }

      this.imageService.uploadImage(this.selectedFile).subscribe(
        (response) => {
          this.predictionResult = response;
          this.loadImages();
          this.selectedFile = null;
          this.predictionResult = null;
        },
        (error) => {
          console.error('Error uploading image:', error);
          console.error('Error details:', error.error);
        }
      );
    }
  }

  loadImages(): void {
    this.imageService.getImages().subscribe(
      (response) => {
        this.images = response.map((image: any) => ({
          ...image,
          file_path: `http://localhost:5000/${image.file_path}`,
          upload_time: new Date(image.upload_time).toLocaleString()
        }));
      },
      (error) => {
        console.error('Error fetching images:', error);
      }
    );
  }

  ngOnInit(): void {
    this.loadImages();
  }

  openCamera(): void {
    this.isCameraOpen = true;
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        this.videoElement.nativeElement.srcObject = stream;
      })
      .catch((error) => {
        console.error('Error accessing the camera:', error);
      });
  }

  closeCamera(): void {
    if (!this.isCameraOpen) return;

    this.isCameraOpen = false;
    const video = this.videoElement.nativeElement;
    const stream = video.srcObject as MediaStream;

    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    video.srcObject = null;
  }

  captureImage(): void {
    const canvas = this.canvasElement.nativeElement;
    const video = this.videoElement.nativeElement;
    const context = canvas.getContext('2d');

    if (!context) {
      console.error('Error: Unable to get canvas context.');
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) {
        const fileName = `captured_image_${Date.now()}.png`;
        this.selectedFile = new File([blob], fileName, { type: 'image/png' });
        this.onUpload();
      }
    }, 'image/png');
  }

  private resetFileSelection(): void {
    this.selectedFile = null;
    this.predictionResult = null;
  }
}
