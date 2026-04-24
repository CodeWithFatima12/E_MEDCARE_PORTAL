from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from .models import Department
from .serializers import DepartmentSerializer

class DepartmentListView(APIView):
    def get(self, request):
        query = request.query_params.get('search', '').strip()
        departments = Department.objects.all()

        if query:
            departments = departments.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)